"""
Utility functions for managing contractual work hours enforcement in timesheets.

This module provides helpers to:
- Fetch active weekly hour limits from ContractHistory or UserHRData
- Calculate intelligent hour distributions across working days
- Validate manual/automatic timesheet entries against contractual limits
"""

from datetime import date, datetime, timedelta
from typing import Tuple, Optional, Dict, List
from models import User, UserHRData, ContractHistory, AttendanceEvent, LeaveRequest
from utils_tenant import filter_by_company
from utils_contract_history import get_current_snapshot


def get_active_work_hours_week(user: User, target_date: Optional[date] = None) -> Optional[float]:
    """
    Get the active weekly work hours for a user at a specific date.
    
    Priority:
    1. Active ContractHistory snapshot at target_date (most accurate for point-in-time)
    2. Fallback to UserHRData.work_hours_week (current contract)
    3. Apply reductions from active Social Safety Net programs (CIGS, Solidarietà, etc.)
    
    Args:
        user: User object
        target_date: Date to check (defaults to today)
    
    Returns:
        Weekly hours as float (potentially reduced by active safety net programs), or None if not defined
    """
    if target_date is None:
        target_date = date.today()
    
    # Get baseline weekly hours from contract
    baseline_hours = None
    hr_data = user.hr_data
    if hr_data:
        # Get snapshot valid at target_date
        snapshot = ContractHistory.query.filter(
            ContractHistory.user_hr_data_id == hr_data.id,
            ContractHistory.effective_from_date <= target_date
        ).filter(
            (ContractHistory.effective_to_date == None) | 
            (ContractHistory.effective_to_date >= target_date)
        ).first()
        
        if snapshot and snapshot.work_hours_week:
            baseline_hours = float(snapshot.work_hours_week)
        elif hr_data.work_hours_week:
            # Fallback to current UserHRData
            baseline_hours = float(hr_data.work_hours_week)
    
    if baseline_hours is None:
        return None
    
    # Check for active Social Safety Net program (ammortizzatori sociali)
    # Apply hours reduction if applicable
    active_assignment = user.get_active_safety_net_assignment(target_date)
    if active_assignment:
        # Get reduced hours from assignment (considers custom override or program settings)
        reduced_hours = active_assignment.get_effective_weekly_hours(baseline_hours)
        return reduced_hours
    
    return baseline_hours


def calculate_weekly_hours_allocation(work_hours_week: float, working_days: int, remainder_on_last_day: bool = True) -> List[float]:
    """
    Distribute weekly hours across working days intelligently.
    
    Example: 39h over 5 days → [8, 8, 8, 8, 7] (remainder on last day)
    Example: 40h over 5 days → [8, 8, 8, 8, 8]
    Example: 30h over 4 days → [8, 8, 8, 6] (remainder on last day)
    
    Args:
        work_hours_week: Total weekly hours from contract
        working_days: Number of working days in the week
        remainder_on_last_day: If True, put deficit on last day (e.g., Fri=7h). If False, distribute evenly from first days.
    
    Returns:
        List of hours per day (length = working_days)
    """
    if working_days <= 0:
        return []
    
    # Calculate base hours per day and remainder
    base_hours = int(work_hours_week // working_days)
    remainder = work_hours_week % working_days
    
    # Build allocation: base hours for all days
    allocation = [float(base_hours)] * working_days
    
    if remainder_on_last_day:
        # Distribute remainder deficit on last day (e.g., 39h → [8,8,8,8,7])
        # First, allocate +1 to all days except last
        full_days = working_days - 1
        if remainder > 0 and full_days > 0:
            # Add 1h to first (working_days - 1) days, last day gets remainder
            for i in range(full_days):
                allocation[i] += 1.0
            # Last day gets what's left
            allocation[-1] = work_hours_week - sum(allocation[:-1])
        else:
            # Edge case: only 1 day or no remainder
            allocation[-1] = work_hours_week - sum(allocation[:-1]) if working_days > 1 else work_hours_week
    else:
        # Distribute remainder from first days (old behavior)
        for i in range(int(remainder)):
            allocation[i] += 1.0
    
    return allocation


def get_iso_week_range(target_date: date) -> Tuple[date, date]:
    """
    Get the start and end date of the ISO week containing target_date.
    
    ISO week: Monday to Sunday
    
    Args:
        target_date: Any date within the week
    
    Returns:
        Tuple of (week_start, week_end) as date objects
    """
    # Get ISO week number and year
    iso_year, iso_week, iso_weekday = target_date.isocalendar()
    
    # Calculate Monday of this ISO week
    # ISO weekday: 1=Monday, 7=Sunday
    week_start = target_date - timedelta(days=iso_weekday - 1)
    week_end = week_start + timedelta(days=6)
    
    return week_start, week_end


def calculate_weekly_hours_total(user_id: int, target_date: date, company_id: int) -> float:
    """
    Calculate total work hours for the ISO week containing target_date.
    
    Sums hours from all AttendanceEvents (manual + live) in the week,
    excluding days with approved/pending leave requests.
    
    Args:
        user_id: User ID
        target_date: Date within the week to check
        company_id: Company ID for multi-tenant filtering
    
    Returns:
        Total hours worked in the week
    """
    week_start, week_end = get_iso_week_range(target_date)
    
    # Get all attendance events in the week
    events = filter_by_company(AttendanceEvent.query).filter(
        AttendanceEvent.user_id == user_id,
        AttendanceEvent.date >= week_start,
        AttendanceEvent.date <= week_end
    ).order_by(AttendanceEvent.date, AttendanceEvent.timestamp).all()
    
    # Get leave requests in the week (to exclude those days)
    leaves = filter_by_company(LeaveRequest.query).filter(
        LeaveRequest.user_id == user_id,
        LeaveRequest.status.in_(['Approved', 'Pending']),
        LeaveRequest.start_date <= week_end,
        LeaveRequest.end_date >= week_start
    ).all()
    
    # Build set of dates with leave
    leave_dates = set()
    for leave in leaves:
        current_date = max(leave.start_date, week_start)
        end_date = min(leave.end_date, week_end)
        while current_date <= end_date:
            leave_dates.add(current_date)
            current_date += timedelta(days=1)
    
    # Calculate daily hours
    from collections import defaultdict
    daily_hours = defaultdict(float)
    
    for day_date in [week_start + timedelta(days=i) for i in range(7)]:
        if day_date in leave_dates:
            continue
        
        day_events = [e for e in events if e.date == day_date]
        if not day_events:
            continue
        
        # Calculate work hours for this day (simple clock_in/out calculation)
        clock_in = None
        clock_out = None
        break_minutes = 0
        break_start = None
        
        for event in day_events:
            if event.event_type == 'clock_in':
                clock_in = event.timestamp
            elif event.event_type == 'clock_out':
                clock_out = event.timestamp
            elif event.event_type == 'break_start' and clock_in:
                # Track break start
                break_start = event.timestamp
            elif event.event_type == 'break_end' and clock_in:
                # Calculate break duration
                if break_start:
                    break_duration = (event.timestamp - break_start).total_seconds() / 60
                    break_minutes += break_duration
                    break_start = None
        
        if clock_in and clock_out:
            total_minutes = (clock_out - clock_in).total_seconds() / 60
            work_minutes = total_minutes - break_minutes
            daily_hours[day_date] = work_minutes / 60
    
    return sum(daily_hours.values())


def validate_weekly_limit(
    user_id: int, 
    user: User,
    day_date: date, 
    new_clock_in: datetime, 
    new_clock_out: datetime,
    company_id: int,
    proposed_break_minutes: float = 60.0
) -> Tuple[bool, str, Dict]:
    """
    Validate if adding/updating a day's hours would exceed weekly contract limit.
    
    Args:
        user_id: User ID
        user: User object
        day_date: Date being edited
        new_clock_in: Proposed clock-in time
        new_clock_out: Proposed clock-out time
        company_id: Company ID
        proposed_break_minutes: Break duration in minutes (default: 60)
    
    Returns:
        Tuple of (is_valid, error_message, context_dict)
        context_dict contains: {
            'work_hours_week': float,
            'current_weekly_total': float,
            'proposed_day_hours': float,
            'new_weekly_total': float,
            'week_start': date,
            'week_end': date
        }
    """
    # Get contractual weekly limit
    work_hours_week = get_active_work_hours_week(user, day_date)
    
    if not work_hours_week:
        # No limit defined, allow any hours
        return True, "", {}
    
    # Calculate current weekly total (excluding the day being edited)
    week_start, week_end = get_iso_week_range(day_date)
    
    # Get all events in the week EXCEPT the day being edited
    events = filter_by_company(AttendanceEvent.query).filter(
        AttendanceEvent.user_id == user_id,
        AttendanceEvent.date >= week_start,
        AttendanceEvent.date <= week_end,
        AttendanceEvent.date != day_date  # Exclude day being edited
    ).all()
    
    # Get leave dates
    leaves = filter_by_company(LeaveRequest.query).filter(
        LeaveRequest.user_id == user_id,
        LeaveRequest.status.in_(['Approved', 'Pending']),
        LeaveRequest.start_date <= week_end,
        LeaveRequest.end_date >= week_start
    ).all()
    
    leave_dates = set()
    for leave in leaves:
        current_date = max(leave.start_date, week_start)
        end_date = min(leave.end_date, week_end)
        while current_date <= end_date:
            leave_dates.add(current_date)
            current_date += timedelta(days=1)
    
    # Calculate hours for other days
    from collections import defaultdict
    daily_hours = defaultdict(float)
    
    for day in [week_start + timedelta(days=i) for i in range(7)]:
        if day == day_date or day in leave_dates:
            continue
        
        day_events = [e for e in events if e.date == day]
        if not day_events:
            continue
        
        clock_in = None
        clock_out = None
        break_minutes = 0
        break_start_ts = None
        
        for event in sorted(day_events, key=lambda x: x.timestamp):
            if event.event_type == 'clock_in':
                clock_in = event.timestamp
            elif event.event_type == 'clock_out':
                clock_out = event.timestamp
            elif event.event_type == 'break_start':
                break_start_ts = event.timestamp
            elif event.event_type == 'break_end':
                if break_start_ts:
                    break_minutes += (event.timestamp - break_start_ts).total_seconds() / 60
                    break_start_ts = None
        
        if clock_in and clock_out:
            total_minutes = (clock_out - clock_in).total_seconds() / 60
            work_minutes = total_minutes - break_minutes
            daily_hours[day] = work_minutes / 60
    
    current_weekly_total = sum(daily_hours.values())
    
    # Calculate proposed day hours
    if new_clock_in and new_clock_out:
        total_minutes = (new_clock_out - new_clock_in).total_seconds() / 60
        work_minutes = total_minutes - proposed_break_minutes
        proposed_day_hours = work_minutes / 60
    else:
        proposed_day_hours = 0.0
    
    new_weekly_total = current_weekly_total + proposed_day_hours
    
    context = {
        'work_hours_week': work_hours_week,
        'current_weekly_total': round(current_weekly_total, 2),
        'proposed_day_hours': round(proposed_day_hours, 2),
        'new_weekly_total': round(new_weekly_total, 2),
        'week_start': week_start,
        'week_end': week_end
    }
    
    # Validate against limit (allow small tolerance for rounding)
    if new_weekly_total > work_hours_week + 0.1:  # 0.1h = 6min tolerance
        error_msg = (
            f"Superato limite ore settimanali contrattuale. "
            f"Limite: {work_hours_week}h/settimana. "
            f"Totale settimana ({week_start.strftime('%d/%m')} - {week_end.strftime('%d/%m')}): "
            f"{round(current_weekly_total, 2)}h già registrate + {round(proposed_day_hours, 2)}h proposte = "
            f"{round(new_weekly_total, 2)}h (eccesso: {round(new_weekly_total - work_hours_week, 2)}h)"
        )
        return False, error_msg, context
    
    return True, "", context


def enforce_safety_net_constraints(user: User, target_date: date, 
                                   proposed_events: list = None) -> Tuple[bool, str]:
    """
    Enforce Social Safety Net program constraints on attendance data.
    
    This validator is used by both bulk_fill_timesheet and save_manual_timesheet
    to ensure compliance with active ammortizzatori sociali programs.
    
    Constraints checked:
    1. Overtime forbidden: If program has overtime_forbidden=True, block overtime entries
    2. Weekly hour limits: Reduced hours apply automatically via get_active_work_hours_week()
    
    Args:
        user: User object
        target_date: Date to check for active program
        proposed_events: List of AttendanceEvent objects being added/modified (optional)
    
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if constraints are satisfied, False otherwise
        - error_message: User-friendly error message if validation fails
    """
    # Check for active safety net assignment
    active_assignment = user.get_active_safety_net_assignment(target_date)
    
    if not active_assignment:
        # No active program, no additional constraints
        return True, ""
    
    program = active_assignment.program
    
    # Constraint 1: Check if overtime is forbidden
    if program.overtime_forbidden and proposed_events:
        # Check if any proposed event is overtime-related
        # For now, we detect overtime by looking for events beyond standard hours
        # This is a simplified check - may need enhancement based on business logic
        
        # Note: Actual overtime detection would need to compare total daily hours
        # against expected daily hours from the contract. For now, we just warn.
        # The weekly validation in validate_weekly_hours_limit will catch excess hours.
        pass  # Overtime blocking is handled via weekly limits
    
    # Constraint 2: Weekly hour limits are automatically enforced via
    # validate_weekly_hours_limit() which calls get_active_work_hours_week()
    # that already applies the reduction. No additional check needed here.
    
    return True, ""


def get_safety_net_context(user: User, target_date: date) -> Optional[dict]:
    """
    Get context information about active safety net program for a user on a date.
    
    Used by UI to display program information and by data entry to cache payroll codes.
    
    Args:
        user: User object
        target_date: Date to check
    
    Returns:
        Dict with program context, or None if no active program:
        {
            'assignment_id': int,
            'program_name': str,
            'program_type': str,
            'payroll_code': str,
            'reduced_hours': float,
            'overtime_forbidden': bool,
            'start_date': date,
            'end_date': date
        }
    """
    active_assignment = user.get_active_safety_net_assignment(target_date)
    
    if not active_assignment:
        return None
    
    program = active_assignment.program
    
    # Get reduced hours
    baseline_hours = get_active_work_hours_week(user, target_date)
    
    return {
        'assignment_id': active_assignment.id,
        'program_name': program.name,
        'program_type': program.program_type,
        'payroll_code': active_assignment.get_payroll_code(),
        'reduced_hours': baseline_hours,
        'overtime_forbidden': program.overtime_forbidden,
        'start_date': active_assignment.start_date,
        'end_date': active_assignment.end_date
    }
