"""
Utility functions for calculating leave and permit balances.

This module provides on-demand calculation of accrued vs. used leave balances
based on employee HR data and approved leave requests, with automatic adjustment
for part-time work and social safety net programs (ammortizzatori sociali).
"""

from decimal import Decimal
from datetime import date, datetime
from typing import Dict, Optional, Any, List, Tuple
from sqlalchemy import and_, or_
from models import User, UserHRData, LeaveRequest, SocialSafetyNetAssignment, db


def get_days_in_month(year: int, month: int) -> int:
    """Get total number of days in a specific month."""
    from datetime import timedelta
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    return last_day.day


def generate_accrual_months(hire_date: Optional[date], reference_date: Optional[date] = None) -> List[Tuple[date, date, Decimal]]:
    """
    Generate list of (month_start, month_end, proration_factor) tuples for accrual calculation.
    
    Args:
        hire_date: Employee hire date
        reference_date: Date to calculate up to (defaults to today)
        
    Returns:
        List of (start_date, end_date, proration_factor) tuples
        proration_factor = days_worked_in_month / total_days_in_month
    """
    if not hire_date:
        return []
    
    if reference_date is None:
        reference_date = date.today()
    
    if hire_date > reference_date:
        return []
    
    months = []
    current = hire_date.replace(day=1)  # Start of hire month
    
    while current <= reference_date:
        # Calculate month end
        from datetime import timedelta
        if current.month == 12:
            month_end = date(current.year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(current.year, current.month + 1, 1) - timedelta(days=1)
        
        # First month: start from hire_date
        month_start = hire_date if current.month == hire_date.month and current.year == hire_date.year else current
        
        # Last month: end at reference_date
        actual_end = month_end if month_end <= reference_date else reference_date
        
        # Calculate proration factor
        days_worked = (actual_end - month_start).days + 1
        total_days = get_days_in_month(current.year, current.month)
        proration_factor = Decimal(str(days_worked)) / Decimal(str(total_days))
        
        months.append((month_start, actual_end, proration_factor))
        
        # Move to next month
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    
    return months


def get_month_reduction_factor(user_id: int, month_start: date, month_end: date, hr_data: UserHRData) -> Decimal:
    """
    Calculate effective reduction factor for a specific month considering part-time and safety net.
    
    Uses day-weighted averaging for safety net programs that cover only part of the month.
    
    Args:
        user_id: User ID
        month_start: Start of accrual period (may be partial month)
        month_end: End of accrual period (may be partial month)
        hr_data: User HR data for part-time info
        
    Returns:
        Reduction factor (1.0 = 100%, 0.5 = 50%, etc.)
    """
    # Apply part-time reduction (applies to entire period)
    part_time_factor = Decimal('1.0')
    if hr_data.part_time_percentage and hr_data.part_time_percentage > 0:
        part_time_factor = Decimal(str(hr_data.part_time_percentage)) / Decimal('100')
    
    # Check for active safety net assignments during this period
    active_assignments = SocialSafetyNetAssignment.query.filter(
        and_(
            SocialSafetyNetAssignment.user_id == user_id,
            SocialSafetyNetAssignment.effective_from <= month_end,
            or_(
                SocialSafetyNetAssignment.effective_to.is_(None),
                SocialSafetyNetAssignment.effective_to >= month_start
            ),
            SocialSafetyNetAssignment.is_approved == True
        )
    ).all()
    
    if not active_assignments:
        # No safety net reduction
        return part_time_factor
    
    # Calculate day-weighted safety net factor
    total_days = (month_end - month_start).days + 1
    weighted_days = Decimal('0')
    
    # For each day in the period, determine which assignment applies (if any)
    from datetime import timedelta
    current_date = month_start
    while current_date <= month_end:
        # Find assignments active on this day
        day_assignments = [
            a for a in active_assignments
            if a.effective_from <= current_date and (a.effective_to is None or a.effective_to >= current_date)
        ]
        
        if day_assignments:
            # Use max reduction if multiple assignments apply
            max_reduction_pct = max(a.program.work_hours_reduction_percentage for a in day_assignments)
            day_factor = Decimal('1.0') - (Decimal(str(max_reduction_pct)) / Decimal('100'))
        else:
            # No assignment on this day
            day_factor = Decimal('1.0')
        
        weighted_days += day_factor
        current_date += timedelta(days=1)
    
    # Calculate average safety net factor across the period
    safety_net_factor = weighted_days / Decimal(str(total_days))
    
    # Combine part-time and safety net multiplicatively
    return part_time_factor * safety_net_factor


def calculate_months_worked(hire_date: Optional[date], reference_date: Optional[date] = None) -> Decimal:
    """
    Calculate the number of months worked since hire date.
    
    Args:
        hire_date: Employee hire date
        reference_date: Date to calculate from (defaults to today)
        
    Returns:
        Number of months worked as Decimal with 2 decimal places
    """
    if not hire_date:
        return Decimal('0')
    
    if reference_date is None:
        reference_date = date.today()
    
    # If hire date is in the future, return 0
    if hire_date > reference_date:
        return Decimal('0')
    
    # Calculate total months
    years_diff = reference_date.year - hire_date.year
    months_diff = reference_date.month - hire_date.month
    days_diff = reference_date.day - hire_date.day
    
    total_months = years_diff * 12 + months_diff
    
    # Add fractional month based on days
    # Approximate: if we're past the hire day, add 1 full month, otherwise prorate
    if days_diff >= 0:
        total_months += 1
    
    return Decimal(str(total_months)).quantize(Decimal('0.01'))


def calculate_leave_balance(user_id: int, reference_date: Optional[date] = None) -> Dict[str, Decimal]:
    """
    Calculate leave (ferie) balance for a user with month-by-month accrual.
    
    Automatically adjusts for:
    - Part-time percentage
    - Social safety net program reductions (ammortizzatori sociali)
    
    Args:
        user_id: User ID
        reference_date: Date to calculate balance as of (defaults to today)
        
    Returns:
        Dictionary with:
            - accrued_days: Total days accrued based on months worked (adjusted for reductions)
            - used_days: Total days used (approved leave requests)
            - balance_days: Remaining balance (accrued - used)
            - monthly_accrual: Base days accrued per month (before reductions)
            - months_worked: Total months worked since hire
    """
    user = User.query.get(user_id)
    if not user or not user.hr_data:
        return {
            'accrued_days': Decimal('0'),
            'used_days': Decimal('0'),
            'balance_days': Decimal('0'),
            'monthly_accrual': Decimal('0'),
            'months_worked': Decimal('0')
        }
    
    hr_data = user.hr_data
    
    # Get monthly accrual rate (default to 0 if not set)
    monthly_accrual = hr_data.gg_ferie_maturate_mese or Decimal('0')
    
    if reference_date is None:
        reference_date = date.today()
    
    # Generate month-by-month accrual periods with proration
    accrual_months = generate_accrual_months(hr_data.hire_date, reference_date)
    
    # Calculate accrued days month-by-month with reductions
    accrued_days = Decimal('0')
    months_worked = Decimal('0')
    
    for month_start, month_end, proration_factor in accrual_months:
        # Get reduction factor for this month (part-time + safety net)
        reduction_factor = get_month_reduction_factor(user_id, month_start, month_end, hr_data)
        
        # Apply proration and reduction to monthly accrual
        month_accrual = monthly_accrual * proration_factor * reduction_factor
        accrued_days += month_accrual
        
        # Accumulate fractional months worked
        months_worked += proration_factor
    
    # Round to 2 decimal places
    accrued_days = accrued_days.quantize(Decimal('0.01'))
    months_worked = months_worked.quantize(Decimal('0.01'))
    
    # Calculate used days from approved leave requests (only Ferie type)
    # Query approved leave requests for this user, type "Ferie", up to reference date
    used_leave = LeaveRequest.query.filter(
        and_(
            LeaveRequest.user_id == user_id,
            LeaveRequest.leave_type == 'Ferie',
            LeaveRequest.status == 'Approved',
            LeaveRequest.start_date <= reference_date
        )
    ).all()
    
    used_days = Decimal('0')
    for leave in used_leave:
        # Calcola i giorni dalla differenza tra start_date e end_date
        if leave.start_date and leave.end_date and not leave.is_time_based():
            days = (leave.end_date - leave.start_date).days + 1
            used_days += Decimal(str(days))
    
    # Calculate balance
    balance_days = accrued_days - used_days
    
    return {
        'accrued_days': accrued_days.quantize(Decimal('0.01')),
        'used_days': used_days.quantize(Decimal('0.01')),
        'balance_days': balance_days.quantize(Decimal('0.01')),
        'monthly_accrual': monthly_accrual,
        'months_worked': months_worked
    }


def calculate_permit_balance(user_id: int, reference_date: Optional[date] = None) -> Dict[str, Decimal]:
    """
    Calculate permit (permessi/ROL) balance for a user with month-by-month accrual.
    
    Automatically adjusts for:
    - Part-time percentage
    - Social safety net program reductions (ammortizzatori sociali)
    
    Args:
        user_id: User ID
        reference_date: Date to calculate balance as of (defaults to today)
        
    Returns:
        Dictionary with:
            - accrued_hours: Total hours accrued based on months worked (adjusted for reductions)
            - used_hours: Total hours used (approved permit requests)
            - balance_hours: Remaining balance (accrued - used)
            - monthly_accrual: Base hours accrued per month (before reductions)
            - months_worked: Total months worked since hire
    """
    user = User.query.get(user_id)
    if not user or not user.hr_data:
        return {
            'accrued_hours': Decimal('0'),
            'used_hours': Decimal('0'),
            'balance_hours': Decimal('0'),
            'monthly_accrual': Decimal('0'),
            'months_worked': Decimal('0')
        }
    
    hr_data = user.hr_data
    
    # Get monthly accrual rate (default to 0 if not set)
    monthly_accrual = hr_data.hh_permesso_maturate_mese or Decimal('0')
    
    if reference_date is None:
        reference_date = date.today()
    
    # Generate month-by-month accrual periods with proration
    accrual_months = generate_accrual_months(hr_data.hire_date, reference_date)
    
    # Calculate accrued hours month-by-month with reductions
    accrued_hours = Decimal('0')
    months_worked = Decimal('0')
    
    for month_start, month_end, proration_factor in accrual_months:
        # Get reduction factor for this month (part-time + safety net)
        reduction_factor = get_month_reduction_factor(user_id, month_start, month_end, hr_data)
        
        # Apply proration and reduction to monthly accrual
        month_accrual = monthly_accrual * proration_factor * reduction_factor
        accrued_hours += month_accrual
        
        # Accumulate fractional months worked
        months_worked += proration_factor
    
    # Round to 2 decimal places
    accrued_hours = accrued_hours.quantize(Decimal('0.01'))
    months_worked = months_worked.quantize(Decimal('0.01'))
    
    # Calculate used hours from approved leave requests (Permesso/ROL types)
    # Query approved permit requests for this user, up to reference date
    # Include "Permesso Retribuito", "ROL", and any other permit-like types
    used_permits = LeaveRequest.query.filter(
        and_(
            LeaveRequest.user_id == user_id,
            or_(
                LeaveRequest.leave_type == 'Permesso Retribuito',
                LeaveRequest.leave_type == 'ROL',
                LeaveRequest.leave_type.like('%Permesso%')
            ),
            LeaveRequest.status == 'Approved',
            LeaveRequest.start_date <= reference_date
        )
    ).all()
    
    used_hours = Decimal('0')
    for permit in used_permits:
        # Calcola le ore usando il metodo get_duration_hours()
        if permit.is_time_based():
            hours = permit.get_duration_hours()
            used_hours += Decimal(str(hours))
    
    # Calculate balance
    balance_hours = accrued_hours - used_hours
    
    return {
        'accrued_hours': accrued_hours.quantize(Decimal('0.01')),
        'used_hours': used_hours.quantize(Decimal('0.01')),
        'balance_hours': balance_hours.quantize(Decimal('0.01')),
        'monthly_accrual': monthly_accrual,
        'months_worked': months_worked
    }


def calculate_combined_balance(user_id: int, reference_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Calculate both leave and permit balances for a user.
    
    Args:
        user_id: User ID
        reference_date: Date to calculate balance as of (defaults to today)
        
    Returns:
        Dictionary with both leave and permit balance information
    """
    leave_balance = calculate_leave_balance(user_id, reference_date)
    permit_balance = calculate_permit_balance(user_id, reference_date)
    
    return {
        'leave': leave_balance,
        'permit': permit_balance,
        'reference_date': reference_date or date.today()
    }


def get_all_leave_balances(company_id: int, reference_date: Optional[date] = None) -> list:
    """
    Get leave and permit balances for all active employees in a company.
    
    Args:
        company_id: Company ID
        reference_date: Date to calculate balances as of (defaults to today)
        
    Returns:
        List of dictionaries with user info and balances
    """
    # Get all active users in the company with HR data (excluding admins)
    users = User.query.join(UserHRData).filter(
        User.company_id == company_id,
        User.active == True,
        User.is_system_admin == False,
        User.role != 'Amministratore'
    ).order_by(User.last_name, User.first_name).all()
    
    balances = []
    for user in users:
        combined_balance = calculate_combined_balance(user.id, reference_date)
        balances.append({
            'user_id': user.id,
            'username': user.username,
            'full_name': f"{user.first_name} {user.last_name}",
            'hire_date': user.hr_data.hire_date if user.hr_data else None,
            'leave': combined_balance['leave'],
            'permit': combined_balance['permit']
        })
    
    return balances
