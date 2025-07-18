from datetime import datetime, date, timedelta, time
from models import User, Shift, LeaveRequest, AttendanceEvent, PresidioCoverage, italian_now
from app import db
import random
import json
import qrcode
from io import BytesIO
import base64
import os
from flask import url_for, request

def is_italian_holiday(check_date):
    """
    Verifica se una data è un giorno festivo in Italia utilizzando il database
    """
    from models import Holiday
    
    # Controlla festività dal database
    holidays = Holiday.query.filter_by(
        month=check_date.month,
        day=check_date.day,
        is_active=True
    ).all()
    
    return len(holidays) > 0

def get_italian_holidays():
    """
    Restituisce tutte le festività italiane attive dal database
    """
    from models import Holiday
    return Holiday.query.filter_by(is_active=True).order_by(Holiday.month, Holiday.day).all()

def format_hours(hours_decimal):
    """
    Converte ore decimali in formato ore e minuti (es: 4.5 -> "4h 30'")
    """
    if hours_decimal is None or hours_decimal == 0:
        return "0h 00'"
    
    # Gestisci valori negativi
    if hours_decimal < 0:
        return "0h 00'"
    
    # Converti in ore e minuti usando round() per arrotondamento corretto
    total_hours = int(hours_decimal)
    minutes = round((hours_decimal - total_hours) * 60)
    
    return f"{total_hours}h {minutes:02d}'"

def generate_static_qr_codes():
    """
    Genera QR code statici per entrata e uscita e li salva nella cartella static/qr
    Restituisce True se la generazione è riuscita, False altrimenti
    """
    try:
        # Crea la cartella se non esiste
        qr_dir = os.path.join('static', 'qr')
        os.makedirs(qr_dir, exist_ok=True)
        
        # Ottieni l'URL base dal contesto della richiesta corrente
        if request:
            base_url = request.url_root.rstrip('/')
        else:
            # Fallback se non c'è contesto di richiesta
            base_url = 'http://localhost:5000'
        
        # URL per entrata e uscita
        urls = {
            'entrata': f"{base_url}/attendance/quick/entrata",
            'uscita': f"{base_url}/attendance/quick/uscita"
        }
        
        # Genera i QR code
        for action, url in urls.items():
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            # Crea l'immagine
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Salva l'immagine
            filename = f"qr_{action}.png"
            filepath = os.path.join(qr_dir, filename)
            img.save(filepath)
        
        return True
        
    except Exception as e:
        print(f"Errore nella generazione QR code: {e}")
        return False

def qr_codes_exist():
    """
    Verifica se i QR code statici esistono
    """
    qr_dir = os.path.join('static', 'qr')
    entrata_path = os.path.join(qr_dir, 'qr_entrata.png')
    uscita_path = os.path.join(qr_dir, 'qr_uscita.png')
    
    return os.path.exists(entrata_path) and os.path.exists(uscita_path)

def get_qr_code_urls():
    """
    Restituisce gli URL per visualizzare i QR code statici se esistono
    """
    if qr_codes_exist():
        return {
            'entrata': url_for('static', filename='qr/qr_entrata.png'),
            'uscita': url_for('static', filename='qr/qr_uscita.png')
        }
    return None

def round_to_half_hour(hour_decimal):
    """
    Arrotonda un orario decimale alla mezz'ora più vicina.
    Es: 11.25 (11:15) → 11.5 (11:30), 11.75 (11:45) → 12.0 (12:00)
    """
    # Converte in mezze ore (0.5 = 30 minuti)
    half_hours = round(hour_decimal * 2) / 2
    return half_hours

def split_coverage_into_max_7h_segments(coverage):
    """
    Divide una copertura in segmenti bilanciati di massimo 7 ore per rispettare 
    i vincoli di lavoro consecutivo. Privilegia la divisione equa del carico 
    invece di assegnare sempre 7h al primo turno.
    """
    MAX_CONSECUTIVE_HOURS = 7
    segments = []
    
    # Calcola la durata totale in ore
    start_hour = coverage.start_time.hour + coverage.start_time.minute / 60.0
    end_hour = coverage.end_time.hour + coverage.end_time.minute / 60.0
    
    # Se la copertura attraversa la mezzanotte
    if end_hour < start_hour:
        end_hour += 24
    
    total_duration = end_hour - start_hour
    
    # Se la durata è <= 7 ore, restituisce la copertura originale
    if total_duration <= MAX_CONSECUTIVE_HOURS:
        segments.append((coverage.start_time, coverage.end_time))
        return segments
    
    # Calcola il numero ottimale di segmenti per bilanciare il carico
    num_segments = int(total_duration / MAX_CONSECUTIVE_HOURS)
    if total_duration % MAX_CONSECUTIVE_HOURS > 0:
        num_segments += 1
    
    # Calcola la durata ideale per segmento (distribuzione equa)
    ideal_segment_duration = total_duration / num_segments
    
    # Se la durata ideale supera 7h, forza più segmenti
    if ideal_segment_duration > MAX_CONSECUTIVE_HOURS:
        num_segments = int(total_duration / MAX_CONSECUTIVE_HOURS) + 1
        ideal_segment_duration = total_duration / num_segments
    
    # Crea i segmenti bilanciati con arrotondamento alle mezze ore
    current_hour = start_hour
    
    for i in range(num_segments):
        if i == num_segments - 1:
            # Ultimo segmento: usa tutto il tempo rimanente (mantiene orario originale di fine)
            segment_end_hour = end_hour
        else:
            # Segmenti intermedi: usa la durata ideale e arrotonda alla mezz'ora
            raw_segment_end = current_hour + ideal_segment_duration
            segment_end_hour = round_to_half_hour(raw_segment_end)
            
            # Assicurati che non superi l'orario di fine o che sia troppo vicino
            if segment_end_hour >= end_hour - 0.5:  # Se meno di 30 min rimanenti
                segment_end_hour = end_hour
        
        # Converte gli orari decimali in oggetti time
        start_time_obj = time(
            hour=int(current_hour) % 24,
            minute=int((current_hour % 1) * 60)
        )
        
        end_time_obj = time(
            hour=int(segment_end_hour) % 24,
            minute=int((segment_end_hour % 1) * 60)
        )
        
        segments.append((start_time_obj, end_time_obj))
        current_hour = segment_end_hour
    
    return segments

def generate_shifts_for_period(start_date, end_date, created_by_id):
    """
    Generate shifts based on configured presidio coverage requirements considering:
    - Configured coverage slots per day/time/role
    - Part-time percentages  
    - Previous workload balancing (favors underutilized users from previous 30 days)
    - Approved leave requests
    - 7-hour consecutive work limit (automatic split into multiple shifts)
    
    Bilanciamento: L'algoritmo favorisce gli utenti con minor utilizzo percentuale 
    nei 30 giorni precedenti, bilanciando automaticamente il carico di lavoro.
    
    Limitazione 7 ore: Coperture superiori a 7h vengono automaticamente divise 
    in turni alternati per rispettare i vincoli di lavoro consecutivo.
    """
    # Get all active coverage configurations valid for the period
    coverage_configs = PresidioCoverage.query.filter(
        PresidioCoverage.is_active == True,
        PresidioCoverage.start_date <= end_date,
        PresidioCoverage.end_date >= start_date
    ).all()
    
    if not coverage_configs:
        return False, "Nessuna copertura presidio valida per il periodo selezionato. Configura prima i requisiti di copertura per le date richieste."
    
    # Get all eligible users (excluding Admin and Ente)
    all_users = User.query.filter_by(active=True).filter(~User.role.in_(['Admin', 'Ente'])).all()
    users_by_role = {}
    for user in all_users:
        if user.role not in users_by_role:
            users_by_role[user.role] = []
        users_by_role[user.role].append(user)
    
    # Get approved leave requests for the period
    leave_requests = LeaveRequest.query.filter(
        LeaveRequest.status == 'Approved',
        LeaveRequest.start_date <= end_date,
        LeaveRequest.end_date >= start_date
    ).all()
    
    # Create a set of dates when each user is on leave
    user_leave_dates = {}
    for leave in leave_requests:
        if leave.user_id not in user_leave_dates:
            user_leave_dates[leave.user_id] = set()
        
        current_date = max(leave.start_date, start_date)
        while current_date <= min(leave.end_date, end_date):
            user_leave_dates[leave.user_id].add(current_date)
            current_date += timedelta(days=1)
    
    # Calculate current period utilization for workload balancing
    # When regenerating, consider only existing shifts in the current period
    current_period_shifts = db.session.query(
        Shift.user_id, 
        db.func.sum(
            db.func.extract('hour', Shift.end_time) + 
            db.func.extract('minute', Shift.end_time) / 60.0 -
            db.func.extract('hour', Shift.start_time) - 
            db.func.extract('minute', Shift.start_time) / 60.0
        ).label('total_hours')
    ).filter(
        Shift.date >= start_date,
        Shift.date <= end_date
    ).group_by(Shift.user_id).all()
    
    # Calculate utilization percentages based on current period
    current_utilization = {}
    period_days = (end_date - start_date).days + 1
    
    for shift_data in current_period_shifts:
        user = User.query.get(shift_data.user_id)
        if user and shift_data.total_hours:
            # Use 1680 annual hours as base calculation
            annual_hours = 1680 * user.part_time_percentage / 100
            theoretical_hours = annual_hours * period_days / 365
            utilization_percent = (shift_data.total_hours / theoretical_hours * 100) if theoretical_hours > 0 else 0
            current_utilization[user.id] = utilization_percent
        else:
            current_utilization[shift_data.user_id] = 0
    
    # Initialize utilization for users without current shifts
    for user in all_users:
        if user.id not in current_utilization:
            current_utilization[user.id] = 0
    
    shifts_created = 0
    shifts = []
    uncovered_shifts = []  # Track shifts that couldn't be assigned
    
    # Generate shifts day by day
    current_date = start_date
    while current_date <= end_date:
        day_of_week = current_date.weekday()  # 0=Monday, 6=Sunday
        
        # Skip holidays for presidio shifts (office is closed)
        if is_italian_holiday(current_date):
            current_date += timedelta(days=1)
            continue
        
        # Track user time assignments to prevent overlapping shifts
        daily_user_assignments = {}
        daily_assigned_users = set()  # Initialize set to track assigned users
        
        # Check existing shifts for this day to avoid duplicates
        existing_shifts = db.session.query(Shift).filter(Shift.date == current_date).all()
        for existing_shift in existing_shifts:
            daily_assigned_users.add(existing_shift.user_id)
            # CRITICAL: Also track the time slots of existing shifts to prevent overlaps
            if existing_shift.user_id not in daily_user_assignments:
                daily_user_assignments[existing_shift.user_id] = []
            daily_user_assignments[existing_shift.user_id].append((existing_shift.start_time, existing_shift.end_time))
        
        # Get coverage requirements for this day
        day_coverages = [c for c in coverage_configs if c.day_of_week == day_of_week]
        
        # FIXED: Group coverages by time slot to consolidate identical time periods
        # Instead of treating each coverage as separate, consolidate coverages with SAME time periods
        # This prevents over-staffing when multiple coverages have identical time slots
        time_slot_groups = {}
        for coverage in day_coverages:
            # Check if this coverage is valid for the current date
            if not coverage.is_valid_for_date(current_date):
                continue
            
            # Split coverage into max 7-hour segments
            coverage_segments = split_coverage_into_max_7h_segments(coverage)
            
            for segment_start, segment_end in coverage_segments:
                slot_key = (segment_start.strftime('%H:%M'), segment_end.strftime('%H:%M'))
                if slot_key not in time_slot_groups:
                    time_slot_groups[slot_key] = []
                time_slot_groups[slot_key].append(coverage)
        
        # Process each time slot group - BUSINESS RULE: ONE PERSON PER REQUIRED ROLE
        for (start_str, end_str), coverages_in_slot in time_slot_groups.items():
            segment_start = datetime.strptime(start_str, '%H:%M').time()
            segment_end = datetime.strptime(end_str, '%H:%M').time()
            
            # NEW LOGIC: Assign ONE person per REQUIRED ROLE (not one person total)
            # This ensures proper coverage: 2 people for Sviluppatore+Redattore slots
            all_required_roles = set()
            for coverage in coverages_in_slot:
                all_required_roles.update(coverage.get_required_roles_list())
            
            # BUSINESS RULE: Each required role needs one dedicated person
            # For Sviluppatore+Redattore slots, this means 2 people total
            
            # Process each required role separately to ensure proper coverage
            for required_role in all_required_roles:
                
                # Find eligible users for this specific role
                eligible_users = users_by_role.get(required_role, [])
                
                # Filter out users on leave for this date
                available_users = [
                    user for user in eligible_users 
                    if user.id not in user_leave_dates or current_date not in user_leave_dates[user.id]
                ]
                
                # Filter based on part-time percentage and current utilization
                # Note: Keep this filter flexible to avoid too many uncovered slots
                ideal_users = [user for user in available_users if should_assign_shift(user, current_date, current_utilization.get(user.id, 0))]
                
                # If ideal users are available, use them; otherwise use all available users
                if ideal_users:
                    available_users = ideal_users
                
                # Filter out users who have overlapping shifts for this specific time slot
                non_overlapping_users = []
                for user in available_users:
                    has_overlap = False
                    if user.id in daily_user_assignments:
                        for existing_start, existing_end in daily_user_assignments[user.id]:
                            # Check if time slots overlap OR are consecutive (no gap between shifts)
                            # Prevent both overlaps and consecutive shifts without break
                            if not (segment_end < existing_start or segment_start > existing_end):
                                has_overlap = True
                                break
                    if not has_overlap:
                        non_overlapping_users.append(user)
                available_users = non_overlapping_users
                
                if available_users:
                    # Enhanced bilanciamento: favorisce utenti con utilizzo molto sotto la media del loro ruolo
                    def get_priority_score(user):
                        current_util = current_utilization.get(user.id, 0)
                        target_util = user.part_time_percentage
                        
                        # Calcola utilizzo medio per ruolo per bilanciamento intelligente
                        role_users = users_by_role.get(user.role, [])
                        role_utilizations = [current_utilization.get(u.id, 0) for u in role_users]
                        avg_role_utilization = sum(role_utilizations) / len(role_utilizations) if role_utilizations else 0
                        
                        # Priorità maggiore per utenti sotto-utilizzati rispetto alla media del ruolo
                        role_gap = max(0, avg_role_utilization - current_util)
                        personal_gap = max(0, target_util - current_util)
                        
                        # Bonus significativo per utenti molto sotto-utilizzati (>20% sotto media ruolo)
                        underutilization_bonus = 1000 if role_gap > 20 else 0
                        
                        # Primary: bonus sottoutilizzo, Secondary: gap personale, Tertiary: utilizzo corrente basso
                        return (-underutilization_bonus, -role_gap, -personal_gap, current_util)
                    
                    available_users.sort(key=get_priority_score)
                    
                    # Assign the best available user for this role in this time slot
                    selected_user = available_users[0]
                else:
                    # FALLBACK: If no ideal users, try any eligible user without utilization filters
                    fallback_users = users_by_role.get(required_role, [])
                    
                    # Filter out users on leave for this date
                    fallback_available = [
                        user for user in fallback_users 
                        if user.id not in user_leave_dates or current_date not in user_leave_dates[user.id]
                    ]
                    
                    # RELAXED POLICY for fallback: Allow overlaps in exceptional cases
                    # First try without overlaps
                    final_fallback = []
                    for user in fallback_available:
                        has_overlap = False
                        if user.id in daily_user_assignments:
                            for existing_start, existing_end in daily_user_assignments[user.id]:
                                # Check if time slots overlap OR are consecutive (no gap between shifts)
                                # Prevent both overlaps and consecutive shifts without break
                                if not (segment_end < existing_start or segment_start > existing_end):
                                    has_overlap = True
                                    break
                        if not has_overlap:
                            final_fallback.append(user)
                    
                    if final_fallback:
                        # Sort by current utilization (lowest first)
                        final_fallback.sort(key=lambda u: current_utilization.get(u.id, 0))
                        selected_user = final_fallback[0]
                    else:
                        # TRULY EXCEPTIONAL: If still no users, track as uncovered
                        # This should be very rare now - only when all users are on leave
                        selected_user = None
                        
                        # Only track as uncovered if truly no users available
                        if not fallback_available:
                            uncovered_shifts.append({
                                'date': current_date,
                                'start_time': segment_start,
                                'end_time': segment_end,
                                'required_roles': [required_role],
                                'reason': f'Nessun {required_role} disponibile per questa data'
                            })
                
                # Only create shift if we found a user for this role
                if selected_user:
                    # Determine shift type based on segment time
                    shift_type = determine_shift_type(segment_start, segment_end)
                    
                    # Calculate segment hours for tracking
                    segment_start_hour = segment_start.hour + segment_start.minute / 60.0
                    segment_end_hour = segment_end.hour + segment_end.minute / 60.0
                    
                    # Handle midnight crossing
                    if segment_end_hour < segment_start_hour:
                        segment_end_hour += 24
                    
                    segment_hours = segment_end_hour - segment_start_hour
                    
                    # Create the shift for this role in this time slot
                    shift = Shift()
                    shift.user_id = selected_user.id
                    shift.date = current_date
                    shift.start_time = segment_start
                    shift.end_time = segment_end
                    shift.shift_type = shift_type
                    shift.created_by = created_by_id
                    shift.created_at = italian_now()
                    
                    shifts.append(shift)
                    shifts_created += 1
                    
                    # Track the specific time assignment to prevent consecutive shifts
                    if selected_user.id not in daily_user_assignments:
                        daily_user_assignments[selected_user.id] = []
                    daily_user_assignments[selected_user.id].append((segment_start, segment_end))
                    
                    # Update utilization tracking
                    current_utilization[selected_user.id] = current_utilization.get(selected_user.id, 0) + segment_hours

        
        current_date += timedelta(days=1)
    
    # Add all created shifts to the database session
    for shift in shifts:
        db.session.add(shift)
    
    try:
        db.session.commit()
        
        # Prepare success message with warnings if needed
        success_message = f"Turnazioni generate con successo: {shifts_created} turni creati con nuovo algoritmo (1 persona per ruolo richiesto) e bilanciamento automatico"
        
        if uncovered_shifts:
            warning_message = f"\n⚠️ ATTENZIONE: {len(uncovered_shifts)} slot non coperti per mancanza di personale disponibile:"
            for uncovered in uncovered_shifts:
                date_str = uncovered['date'].strftime('%d/%m/%Y')
                time_str = f"{uncovered['start_time'].strftime('%H:%M')}-{uncovered['end_time'].strftime('%H:%M')}"
                roles_str = ', '.join(uncovered['required_roles'])
                warning_message += f"\n• {date_str} {time_str} (ruoli: {roles_str}) - {uncovered['reason']}"
            
            success_message += warning_message
            
        return True, success_message
            
    except Exception as e:
        db.session.rollback()
        return False, f"Errore durante la generazione: {str(e)}"


def determine_shift_type(start_time, end_time):
    """
    Determine shift type based on start and end times
    """
    start_hour = start_time.hour
    
    if start_hour < 10:
        return 'Mattina'
    elif start_hour < 14:
        return 'Pomeriggio'
    else:
        return 'Sera'

def should_assign_shift(user, date, current_utilization=0):
    """
    Determine if a user should be assigned a shift based on their part-time percentage
    and current utilization to ensure balanced distribution
    """
    if user.part_time_percentage >= 100:
        return True
    
    # For part-time workers, use a more deterministic approach based on current utilization
    # If current utilization is below their target percentage, they should be available for shifts
    target_utilization = user.part_time_percentage
    
    # Allow some tolerance (10%) to account for scheduling variations
    tolerance = 10
    return current_utilization < (target_utilization + tolerance)

def get_user_statistics(user_id, start_date=None, end_date=None):
    """
    Get comprehensive statistics for a user
    """
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()
    
    # Attendance statistics using AttendanceEvent
    total_hours = 0
    days_worked = 0
    
    # Calculate hours and days from AttendanceEvent system
    from models import AttendanceEvent
    
    current_date = start_date
    while current_date <= end_date:
        try:
            daily_hours = AttendanceEvent.get_daily_work_hours(user_id, current_date)
            if daily_hours > 0:
                total_hours += daily_hours
                days_worked += 1
        except Exception as e:
            print(f"Error calculating daily hours for user {user_id} on {current_date}: {e}")
            # Continue with 0 hours for this day
        current_date += timedelta(days=1)
    
    # Removed shift statistics - no longer tracking shifts
    shifts_assigned = 0
    shifts_past = 0
    shifts_future = 0
    shift_hours = 0
    
    # Leave statistics
    leave_requests = LeaveRequest.query.filter(
        LeaveRequest.user_id == user_id,
        LeaveRequest.start_date >= start_date,
        LeaveRequest.end_date <= end_date
    ).all()
    
    approved_leaves = len([l for l in leave_requests if l.status == 'Approved'])
    pending_leaves = len([l for l in leave_requests if l.status == 'Pending'])
    
    # Statistiche interventi generici
    from models import Intervention
    
    try:
        # Converti le date in datetime per il confronto corretto
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        interventions = Intervention.query.filter(
            Intervention.user_id == user_id,
            Intervention.start_datetime >= start_datetime,
            Intervention.start_datetime <= end_datetime
        ).all()
    except Exception as e:
        print(f"Error loading interventions for user {user_id}: {e}")
        interventions = []
    
    total_interventions = len(interventions)
    completed_interventions = [i for i in interventions if i.end_datetime is not None]
    active_interventions = total_interventions - len(completed_interventions)
    
    # Calcola tempi di risoluzione (solo per interventi completati)
    resolution_times = []
    total_intervention_minutes = 0
    onsite_interventions = total_interventions  # Tutti gli interventi generici sono in presenza
    remote_interventions = 0  # Nessun intervento generico è remoto
    
    for intervention in completed_interventions:
        duration = intervention.duration_minutes
        if duration and duration > 0:
            resolution_times.append(duration)
            total_intervention_minutes += duration
    
    # Calcola statistiche tempi
    avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0
    min_resolution_time = min(resolution_times) if resolution_times else 0
    max_resolution_time = max(resolution_times) if resolution_times else 0
    
    return {
        'total_hours_worked': round(total_hours, 2),
        'days_worked': days_worked,
        'shifts_assigned': shifts_assigned,
        'shifts_past': shifts_past,
        'shifts_future': shifts_future,
        'shift_hours': round(shift_hours, 2),
        'approved_leaves': approved_leaves,
        'pending_leaves': pending_leaves,
        # Statistiche reperibilità
        'total_interventions': total_interventions,
        'completed_interventions': len(completed_interventions),
        'active_interventions': active_interventions,
        'avg_resolution_time_minutes': round(avg_resolution_time, 1),
        'min_resolution_time_minutes': min_resolution_time,
        'max_resolution_time_minutes': max_resolution_time,
        'total_intervention_hours': round(total_intervention_minutes / 60, 2),
        'remote_interventions': remote_interventions,
        'onsite_interventions': onsite_interventions
    }

def get_team_statistics(start_date=None, end_date=None):
    """
    Get team-wide statistics - simplified version to avoid timeouts
    """
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()
    
    try:
        # Active users (excluding Admin and Ente)
        active_users = User.query.filter(User.active.is_(True)).filter(~User.role.in_(['Admin', 'Ente'])).count()
        
        # Simplified total hours calculation - just count events
        from models import AttendanceEvent
        total_events = AttendanceEvent.query.filter(
            AttendanceEvent.date >= start_date,
            AttendanceEvent.date <= end_date,
            AttendanceEvent.event_type == 'clock_in'
        ).count()
        
        # Estimate hours: assume 8 hours per day worked
        estimated_hours = total_events * 8
        
        # Pending leave requests
        pending_leaves = LeaveRequest.query.filter(
            LeaveRequest.status == 'Pending'
        ).count()
        
        # Removed shifts functionality
        
        # Detailed intervention stats
        from models import ReperibilitaIntervention
        from datetime import datetime
        
        team_start_datetime = datetime.combine(start_date, datetime.min.time())
        team_end_datetime = datetime.combine(end_date, datetime.max.time())
        
        # Get all interventions for the period
        team_interventions = ReperibilitaIntervention.query.filter(
            ReperibilitaIntervention.start_datetime >= team_start_datetime,
            ReperibilitaIntervention.start_datetime <= team_end_datetime
        ).all()
        
        total_team_interventions = len(team_interventions)
        completed_team_interventions = [i for i in team_interventions if i.end_datetime is not None]
        active_team_interventions = total_team_interventions - len(completed_team_interventions)
        
        # Calculate detailed statistics
        team_resolution_times = []
        total_team_intervention_hours = 0
        team_remote_interventions = 0
        team_onsite_interventions = 0
        
        # Process all interventions for remote/onsite count and completed ones for duration
        for intervention in team_interventions:
            # Count remote vs onsite for ALL interventions
            if intervention.is_remote:
                team_remote_interventions += 1
            else:
                team_onsite_interventions += 1
            
            # Only calculate duration stats for completed interventions
            if intervention.end_datetime is not None:
                duration = intervention.duration_minutes
                if duration and duration > 0:
                    team_resolution_times.append(duration)
                    total_team_intervention_hours += duration / 60
        
        team_avg_resolution_time = sum(team_resolution_times) / len(team_resolution_times) if team_resolution_times else 0
        
        return {
            'active_users': active_users,
            'total_hours': round(estimated_hours, 2),
            'pending_leaves': pending_leaves,
            'avg_hours_per_user': round(estimated_hours / active_users if active_users > 0 else 0, 2),
            # Statistiche reperibilità team dettagliate
            'total_team_interventions': total_team_interventions,
            'completed_team_interventions': len(completed_team_interventions),
            'active_team_interventions': active_team_interventions,
            'team_avg_resolution_time_minutes': round(team_avg_resolution_time, 1),
            'total_team_intervention_hours': round(total_team_intervention_hours, 2),
            'team_remote_interventions': team_remote_interventions,
            'team_onsite_interventions': team_onsite_interventions
        }
        
    except Exception as e:
        print(f"Error in get_team_statistics: {e}")
        return {
            'active_users': 0,
            'total_hours': 0,
            'pending_leaves': 0,
            'avg_hours_per_user': 0,
            'total_team_interventions': 0,
            'completed_team_interventions': 0,
            'active_team_interventions': 0,
            'team_avg_resolution_time_minutes': 0,
            'total_team_intervention_hours': 0,
            'team_remote_interventions': 0,
            'team_onsite_interventions': 0
        }

def check_user_shift_schedule(user_id, check_datetime=None):
    """
    Check if a user has a scheduled shift for the given datetime.
    Returns a tuple (has_shift, shift_info, warning_message)
    
    Args:
        user_id: ID of the user to check
        check_datetime: datetime to check (defaults to now)
    
    Returns:
        tuple: (bool, dict|None, str|None)
            - has_shift: True if user has a shift at this time
            - shift_info: dict with shift details if found
            - warning_message: warning message if no shift found
    """
    if not check_datetime:
        check_datetime = datetime.now()
    
    check_date = check_datetime.date()
    check_time = check_datetime.time()
    
    # Find shifts for this user on this date
    shifts = Shift.query.filter_by(
        user_id=user_id,
        date=check_date
    ).all()
    
    if not shifts:
        return False, None, f"Nessun turno programmato per oggi ({check_date.strftime('%d/%m/%Y')}). Registrazione comunque consentita."
    
    # Check if current time falls within any scheduled shift
    for shift in shifts:
        # Convert times to datetime objects for comparison - ensure timezone aware
        shift_start = datetime.combine(check_date, shift.start_time)
        shift_end = datetime.combine(check_date, shift.end_time)
        
        # Make them timezone aware if check_datetime has timezone
        if check_datetime.tzinfo is not None:
            # Get the timezone from check_datetime
            tz = check_datetime.tzinfo
            shift_start = shift_start.replace(tzinfo=tz)
            shift_end = shift_end.replace(tzinfo=tz)
        
        # Handle shifts that cross midnight
        if shift.end_time < shift.start_time:
            shift_end = shift_end + timedelta(days=1)
        
        # Allow some flexibility (30 minutes before start, 1 hour after end)
        tolerance_start = shift_start - timedelta(minutes=30)
        tolerance_end = shift_end + timedelta(hours=1)
        
        # Ensure tolerance times also have timezone
        if check_datetime.tzinfo is not None:
            tz = check_datetime.tzinfo
            if tolerance_start.tzinfo is None:
                tolerance_start = tolerance_start.replace(tzinfo=tz)
            if tolerance_end.tzinfo is None:
                tolerance_end = tolerance_end.replace(tzinfo=tz)
        
        if tolerance_start <= check_datetime <= tolerance_end:
            shift_info = {
                'id': shift.id,
                'start_time': shift.start_time.strftime('%H:%M'),
                'end_time': shift.end_time.strftime('%H:%M'),
                'shift_type': shift.shift_type,
                'is_within_schedule': shift_start <= check_datetime <= shift_end,
                'is_early': check_datetime < shift_start,
                'is_late': check_datetime > shift_end
            }
            return True, shift_info, None
    
    # User has shifts today but not at this time
    shift_times = [f"{s.start_time.strftime('%H:%M')}-{s.end_time.strftime('%H:%M')}" for s in shifts]
    warning_msg = f"Turno non programmato per questo orario. I tuoi turni di oggi: {', '.join(shift_times)}. Registrazione comunque consentita."
    
    return False, None, warning_msg


def generate_reperibilita_shifts(start_date, end_date, created_by_id):
    """
    Genera turni di reperibilità basati sulle coperture definite
    """
    from models import User, ReperibilitaCoverage, ReperibilitaShift, LeaveRequest
    from app import db
    import json
    from datetime import timedelta
    from collections import defaultdict
    
    # Get all users grouped by role (excluding Admin and Ente)
    all_users = User.query.filter_by(active=True).filter(~User.role.in_(['Admin', 'Ente'])).all()
    users_by_role = defaultdict(list)
    for user in all_users:
        users_by_role[user.role].append(user)
    
    # Get coverage configurations for the time period
    coverage_configs = ReperibilitaCoverage.query.filter(
        ReperibilitaCoverage.is_active == True
    ).all()
    
    # Get leave requests for the period
    leave_requests = LeaveRequest.query.filter(
        LeaveRequest.status.in_(['Pending', 'Approved']),
        LeaveRequest.start_date <= end_date,
        LeaveRequest.end_date >= start_date
    ).all()
    
    # Build leave dates mapping
    user_leave_dates = defaultdict(set)
    for leave in leave_requests:
        current_date = max(leave.start_date, start_date)
        while current_date <= min(leave.end_date, end_date):
            user_leave_dates[leave.user_id].add(current_date)
            current_date += timedelta(days=1)
    
    # Calculate current period utilization for reperibilità balancing
    current_period_shifts = db.session.query(
        ReperibilitaShift.user_id, 
        db.func.sum(
            db.func.extract('hour', ReperibilitaShift.end_time) + 
            db.func.extract('minute', ReperibilitaShift.end_time) / 60.0 -
            db.func.extract('hour', ReperibilitaShift.start_time) - 
            db.func.extract('minute', ReperibilitaShift.start_time) / 60.0
        ).label('total_hours')
    ).filter(
        ReperibilitaShift.date >= start_date,
        ReperibilitaShift.date <= end_date
    ).group_by(ReperibilitaShift.user_id).all()
    
    # Calculate utilization percentages for reperibilità
    current_utilization = {}
    period_days = (end_date - start_date).days + 1
    
    for shift_data in current_period_shifts:
        user = User.query.get(shift_data.user_id)
        if user and shift_data.total_hours:
            # For reperibilità, use a reduced percentage of normal capacity
            reperibilita_capacity = 0.3  # 30% of normal capacity for on-call duties
            annual_hours = 1680 * user.part_time_percentage / 100 * reperibilita_capacity
            theoretical_hours = annual_hours * period_days / 365
            utilization_percent = (shift_data.total_hours / theoretical_hours * 100) if theoretical_hours > 0 else 0
            current_utilization[user.id] = utilization_percent
        else:
            current_utilization[shift_data.user_id] = 0
    
    # Initialize utilization for users without current shifts
    for user in all_users:
        if user.id not in current_utilization:
            current_utilization[user.id] = 0
    
    shifts_created = 0
    coverage_warnings = []
    
    # Generate reperibilità shifts day by day
    current_date = start_date
    while current_date <= end_date:
        day_of_week = current_date.weekday()  # 0=Monday, 6=Sunday
        
        # Get coverage requirements for this day
        day_coverages = [c for c in coverage_configs if c.day_of_week == day_of_week]
        
        # Add holiday coverages if this date is a holiday
        if is_italian_holiday(current_date):
            holiday_coverages = [c for c in coverage_configs if c.day_of_week == 7]  # 7 = Festivi
            day_coverages.extend(holiday_coverages)
        
        for coverage in day_coverages:
            # Check if this coverage is valid for the current date
            if not coverage.is_valid_for_date(current_date):
                continue
                
            # Get required roles for this coverage slot
            required_roles = coverage.get_required_roles_list()
            
            # For reperibilità, we typically assign one person per shift (no segmentation needed)
            # Find eligible users for any of the required roles
            eligible_users = []
            for role in required_roles:
                if role in users_by_role:
                    eligible_users.extend(users_by_role[role])
            
            # Remove duplicates and filter out users on leave
            available_users = [
                user for user in set(eligible_users)
                if user.id not in user_leave_dates or current_date not in user_leave_dates[user.id]
            ]
            
            # If no users available from required roles, expand to all active users to ensure coverage
            if not available_users:
                available_users = [
                    user for user in all_users 
                    if user.id not in user_leave_dates or current_date not in user_leave_dates[user.id]
                ]
            
            # Filter based on reperibilità capacity (independent from presidio shifts)
            preferred_users = [user for user in available_users if should_assign_reperibilita_shift(user, current_date, current_utilization.get(user.id, 0))]
            
            # If no preferred users, use all available users to ensure coverage
            final_available_users = preferred_users if preferred_users else available_users
            
            if final_available_users:
                # Sort by priority for reperibilità assignment (simple version)
                def get_reperibilita_priority_score(user):
                    # Use only current utilization to avoid database query issues
                    current_util = current_utilization.get(user.id, 0)
                    return current_util
                
                final_available_users.sort(key=get_reperibilita_priority_score)
                
                # Assign the best available user (lowest score)
                selected_user = final_available_users[0]
                
                # Check if we had to use fallback to users outside required roles
                role_fallback_used = selected_user.role not in required_roles if required_roles else False
                
                # Calculate shift hours for tracking
                start_hour = coverage.start_time.hour + coverage.start_time.minute / 60.0
                end_hour = coverage.end_time.hour + coverage.end_time.minute / 60.0
                
                # Handle overnight shifts
                if end_hour < start_hour:
                    end_hour += 24
                
                shift_hours = end_hour - start_hour
                
                # Create the reperibilità shift
                shift = ReperibilitaShift()
                shift.user_id = selected_user.id
                shift.date = current_date
                shift.start_time = coverage.start_time
                shift.end_time = coverage.end_time
                shift.description = coverage.description or f"Reperibilità {coverage.get_day_name()}"
                shift.created_by = created_by_id
                db.session.add(shift)
                
                # Update reperibilità utilization tracking (independent from presidio)
                if selected_user.id not in current_utilization:
                    current_utilization[selected_user.id] = 0
                
                # Simply add hours without complex percentage calculations for reperibilità
                current_utilization[selected_user.id] += shift_hours
                
                # Add informational warning if we used a different role
                if role_fallback_used:
                    required_roles_str = " o ".join(required_roles) if len(required_roles) > 1 else required_roles[0]
                    time_range = f"{coverage.start_time.strftime('%H:%M')}-{coverage.end_time.strftime('%H:%M')}"
                    fallback_warning = f"{current_date.strftime('%d/%m/%Y')} {time_range}: Assegnato {selected_user.role} {selected_user.first_name} {selected_user.last_name} (richiesto: {required_roles_str})"
                    coverage_warnings.append(fallback_warning)
                
                shifts_created += 1
            else:
                # This should only happen if ALL users in the system are on leave for this date
                # which is extremely unlikely but we handle it gracefully
                roles_str = " o ".join(required_roles) if len(required_roles) > 1 else required_roles[0] if required_roles else "utente"
                time_range = f"{coverage.start_time.strftime('%H:%M')}-{coverage.end_time.strftime('%H:%M')}"
                
                total_users = len(all_users)
                users_on_leave = len([user for user in all_users 
                                     if user.id in user_leave_dates and current_date in user_leave_dates[user.id]])
                
                warning = f"{current_date.strftime('%d/%m/%Y')} {time_range}: Impossibile assegnare reperibilità - tutti gli utenti in ferie ({users_on_leave}/{total_users})"
                coverage_warnings.append(warning)
        
        current_date += timedelta(days=1)
    
    # Commit all changes
    try:
        db.session.commit()
        return shifts_created, coverage_warnings
    except Exception as e:
        db.session.rollback()
        raise e


def should_assign_reperibilita_shift(user, date, current_reperibilita_utilization):
    """
    Determina se un utente dovrebbe ricevere un turno di reperibilità
    La reperibilità è indipendente dai turni di presidio fisici
    """
    # Per ora disabilito i controlli problematici e uso solo il limite base
    # TODO: riattivare controlli per mattina successiva e turni serali quando risolto bug SQLAlchemy
    max_reperibilita_utilization = user.part_time_percentage * 1.0  # 100% del part-time per reperibilità
    return current_reperibilita_utilization < max_reperibilita_utilization
