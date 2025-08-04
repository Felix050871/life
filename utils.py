from datetime import datetime, date, timedelta, time
from models import User, LeaveRequest, AttendanceEvent, PresidioCoverage, Shift, WorkSchedule, italian_now
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
        active=True
    ).all()
    
    return len(holidays) > 0

def get_italian_holidays():
    """
    Restituisce tutte le festività italiane attive dal database
    """
    from models import Holiday
    return Holiday.query.filter_by(active=True).order_by(Holiday.month, Holiday.day).all()

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
        # Ottieni configurazione per paths
        from config import get_config
        config = get_config()
        qr_dir = config.STATIC_QR_DIR
        os.makedirs(qr_dir, exist_ok=True)
        
        # Ottieni l'URL base dal contesto della richiesta corrente
        if request:
            base_url = request.url_root.rstrip('/')
        else:
            # Fallback se non c'è contesto di richiesta - usa configurazione centralizzata
            from config import get_config
            config = get_config()
            base_url = config.BASE_URL
        
        # URL per entrata e uscita - corretti per corrispondenza route
        urls = {
            'entrata': f"{base_url}/qr_login/entrata",
            'uscita': f"{base_url}/qr_login/uscita"
        }
        
        # Ottieni configurazione QR centralizzata
        from config import get_config
        config = get_config()
        
        # Genera i QR code
        for action, url in urls.items():
            qr = qrcode.QRCode(
                version=config.QR_CODE_VERSION,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=config.QR_CODE_BOX_SIZE,
                border=config.QR_CODE_BORDER,
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
        pass  # Silent error handling
        return False

def qr_codes_exist():
    """
    Verifica se i QR code statici esistono
    """
    from config import get_config
    config = get_config()
    qr_dir = config.STATIC_QR_DIR
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

def get_shift_type_from_time(start_time, end_time):
    """
    Determina il tipo di turno basandosi sull'orario.
    Returns: 'mattina', 'pomeriggio', 'sera', 'notte'
    """
    start_hour = start_time.hour
    end_hour = end_time.hour
    
    # Se il turno attraversa la mezzanotte
    if end_hour < start_hour:
        return 'notte'
    
    # Classificazione basata sull'orario di inizio
    if start_hour >= 6 and start_hour < 14:
        return 'mattina'
    elif start_hour >= 14 and start_hour < 19:
        return 'pomeriggio'  
    elif start_hour >= 19 and start_hour < 23:
        return 'sera'
    else:  # 23:00-06:00
        return 'notte'

def check_weekly_rest_compliance(user_id, week_start_date, new_shift_date):
    """
    Verifica se l'utente rispetta i requisiti di riposo settimanale (almeno 2 giorni).
    
    Args:
        user_id: ID dell'utente
        week_start_date: Data di inizio della settimana (lunedì)
        new_shift_date: Data del nuovo turno da assegnare
    
    Returns:
        dict: {
            'compliant': bool,
            'work_days_count': int,
            'rest_days_remaining': int,
            'penalty_score': int
        }
    """
    from datetime import timedelta
    
    # Calcola le date della settimana (lunedì-domenica)
    week_dates = []
    for i in range(7):
        week_dates.append(week_start_date + timedelta(days=i))
    
    # Conta i giorni lavorativi nella settimana (escluso il nuovo turno)
    work_days = set()
    
    # Controlla turni presidio
    presidio_shifts = Shift.query.filter(
        Shift.user_id == user_id,
        Shift.date >= week_start_date,
        Shift.date < week_start_date + timedelta(days=7),
        Shift.date != new_shift_date  # Escludi il nuovo turno che stiamo valutando
    ).all()
    
    for shift in presidio_shifts:
        work_days.add(shift.date)
    
    # Controlla turni reperibilità
    from models import ReperibilitaShift
    reperibilita_shifts = ReperibilitaShift.query.filter(
        ReperibilitaShift.user_id == user_id,
        ReperibilitaShift.date >= week_start_date,
        ReperibilitaShift.date < week_start_date + timedelta(days=7),
        ReperibilitaShift.date != new_shift_date
    ).all()
    
    for shift in reperibilita_shifts:
        work_days.add(shift.date)
    
    # Aggiungi il nuovo turno
    work_days.add(new_shift_date)
    
    work_days_count = len(work_days)
    rest_days_count = 7 - work_days_count
    
    # Requisito: almeno 2 giorni di riposo settimanali
    min_rest_days = 2
    compliant = rest_days_count >= min_rest_days
    
    # Calcola penalità progressiva
    penalty_score = 0
    if rest_days_count < min_rest_days:
        if rest_days_count == 1:
            penalty_score = 8000  # ALTA penalità per solo 1 giorno di riposo
        elif rest_days_count == 0:
            penalty_score = 15000  # MASSIMA penalità per nessun giorno di riposo
    
    return {
        'compliant': compliant,
        'work_days_count': work_days_count,
        'rest_days_remaining': rest_days_count,
        'penalty_score': penalty_score
    }

def check_weekly_hours_compliance(user_id, week_start_date, new_shift_start, new_shift_end):
    """
    Verifica se l'utente rispetta il limite di 40 ore settimanali (per utenti al 100%).
    
    Args:
        user_id: ID dell'utente
        week_start_date: Data di inizio della settimana (lunedì)
        new_shift_start: Orario inizio nuovo turno
        new_shift_end: Orario fine nuovo turno
    
    Returns:
        dict: {
            'compliant': bool,
            'current_hours': float,
            'max_hours': float,
            'hours_after_new_shift': float,
            'penalty_score': int
        }
    """
    from datetime import timedelta
    
    # Ottieni l'utente per verificare la percentuale part-time
    user = User.query.get(user_id)
    if not user:
        return {'compliant': True, 'current_hours': 0, 'max_hours': 40, 'hours_after_new_shift': 0, 'penalty_score': 0}
    
    # Calcola ore massime settimanali basate sulla percentuale part-time
    base_weekly_hours = 40.0
    max_weekly_hours = base_weekly_hours * (user.part_time_percentage / 100.0)
    
    # Calcola ore già lavorate nella settimana
    current_hours = 0.0
    
    # Conta ore dai turni presidio
    presidio_shifts = Shift.query.filter(
        Shift.user_id == user_id,
        Shift.date >= week_start_date,
        Shift.date < week_start_date + timedelta(days=7)
    ).all()
    
    for shift in presidio_shifts:
        shift_hours = get_shift_duration_hours(shift.start_time, shift.end_time)
        current_hours += shift_hours
    
    # Conta ore dai turni reperibilità
    from models import ReperibilitaShift
    reperibilita_shifts = ReperibilitaShift.query.filter(
        ReperibilitaShift.user_id == user_id,
        ReperibilitaShift.date >= week_start_date,
        ReperibilitaShift.date < week_start_date + timedelta(days=7)
    ).all()
    
    for shift in reperibilita_shifts:
        shift_hours = get_shift_duration_hours(shift.start_time, shift.end_time)
        current_hours += shift_hours
    
    # Calcola ore del nuovo turno
    new_shift_hours = get_shift_duration_hours(new_shift_start, new_shift_end)
    hours_after_new_shift = current_hours + new_shift_hours
    
    # Verifica compliance
    compliant = hours_after_new_shift <= max_weekly_hours
    
    # Calcola penalità progressiva per superamento ore
    penalty_score = 0
    if hours_after_new_shift > max_weekly_hours:
        overtime_hours = hours_after_new_shift - max_weekly_hours
        if overtime_hours <= 2:
            penalty_score = 3000  # MEDIA penalità per superamento fino a 2h
        elif overtime_hours <= 5:
            penalty_score = 6000  # ALTA penalità per superamento fino a 5h
        else:
            penalty_score = 12000  # MASSIMA penalità per superamento oltre 5h
    
    return {
        'compliant': compliant,
        'current_hours': current_hours,
        'max_hours': max_weekly_hours,
        'hours_after_new_shift': hours_after_new_shift,
        'penalty_score': penalty_score
    }

def get_rest_period_penalty(user_id, current_date, new_start_time, new_end_time):
    """
    Calcola penalità per assegnazioni che violano i periodi di riposo necessari.
    Evita situazioni come: turno notturno seguito da turno mattutino il giorno successivo.
    
    Returns: penalty score (0 = nessuna penalità, valori positivi = penalità crescenti)
    """
    penalty = 0
    
    # Controlla i turni del giorno precedente
    previous_date = current_date - timedelta(days=1)
    previous_shifts = Shift.query.filter(
        Shift.user_id == user_id,
        Shift.date == previous_date
    ).all()
    
    # Controlla i turni del giorno successivo (se già assegnati)
    next_date = current_date + timedelta(days=1)
    next_shifts = Shift.query.filter(
        Shift.user_id == user_id,
        Shift.date == next_date
    ).all()
    
    new_shift_type = get_shift_type_from_time(new_start_time, new_end_time)
    
    # Regole di penalità per turni consecutivi inappropriati
    for prev_shift in previous_shifts:
        prev_shift_type = get_shift_type_from_time(prev_shift.start_time, prev_shift.end_time)
        
        # Penalità MASSIMA: turno notturno seguito da turno mattutino
        if prev_shift_type == 'notte' and new_shift_type == 'mattina':
            penalty += 10000  # Penalità molto alta per evitare questa combinazione
        
        # Penalità ALTA: turno sera tardi seguito da turno mattutino presto
        elif (prev_shift_type == 'sera' and new_shift_type == 'mattina' and 
              prev_shift.end_time.hour >= 22 and new_start_time.hour <= 7):
            penalty += 5000
        
        # Penalità MEDIA: turni lunghi consecutivi (>6 ore ciascuno)
        elif (get_shift_duration_hours(prev_shift.start_time, prev_shift.end_time) >= 6 and
              get_shift_duration_hours(new_start_time, new_end_time) >= 6):
            penalty += 1000
    
    # Controlla anche turni nel giorno corrente per evitare sovraccarico
    current_shifts = Shift.query.filter(
        Shift.user_id == user_id,
        Shift.date == current_date
    ).all()
    
    total_daily_hours = sum([
        get_shift_duration_hours(shift.start_time, shift.end_time) 
        for shift in current_shifts
    ])
    
    new_shift_hours = get_shift_duration_hours(new_start_time, new_end_time)
    
    # Penalità per superamento ore giornaliere raccomandate
    user = User.query.get(user_id)
    max_daily_hours = get_user_max_daily_hours(user) if user else 8.0
    
    if total_daily_hours + new_shift_hours > max_daily_hours:
        penalty += 2000  # Penalità per superamento capacità giornaliera
    
    # NUOVO: Controllo riposo settimanale (almeno 2 giorni)
    week_start = current_date - timedelta(days=current_date.weekday())  # Lunedì della settimana
    weekly_rest_check = check_weekly_rest_compliance(user_id, week_start, current_date)
    penalty += weekly_rest_check['penalty_score']
    
    # NUOVO: Controllo ore settimanali (40h per 100%, proporzionale per part-time)
    weekly_hours_check = check_weekly_hours_compliance(user_id, week_start, new_start_time, new_end_time)
    penalty += weekly_hours_check['penalty_score']
    
    return penalty

def get_shift_duration_hours(start_time, end_time):
    """
    Calcola la durata di un turno in ore decimali.
    """
    start_hour = start_time.hour + start_time.minute / 60.0
    end_hour = end_time.hour + end_time.minute / 60.0
    
    # Gestisce turni che attraversano la mezzanotte
    if end_hour < start_hour:
        end_hour += 24
    
    return end_hour - start_hour

def get_user_max_daily_hours(user):
    """
    Calcola l'orario massimo lavorabile giornaliero per un utente.
    - 8 ore per utenti al 100%
    - Proporzione per part-time (es: 50% = 4 ore max)
    - Mai superiore a 8 ore assolute
    """
    if not user or not user.part_time_percentage:
        return 8.0
    
    # 8 ore base per giornata lavorativa completa
    base_hours = 8.0
    part_time_hours = base_hours * (user.part_time_percentage / 100.0)
    
    # LIMITE ASSOLUTO: mai superiore a 8 ore, anche per utenti al 100%
    max_hours = min(part_time_hours, 8.0)
    
    # Minimo 2 ore anche per part-time molto bassi per evitare turni troppo frammentati
    return max(max_hours, 2.0)

def split_coverage_into_segments_by_user_capacity(coverage, available_users):
    """
    Divide una copertura in segmenti basati sulla capacità lavorativa degli utenti disponibili.
    Se la copertura eccede la capacità di un singolo utente, la divide automaticamente.
    
    REGOLA CRITICA: Nessun utente può lavorare più di 8 ore consecutive.
    
    Args:
        coverage: Oggetto copertura da dividere
        available_users: Lista degli utenti disponibili per la copertura
    
    Returns:
        Lista di tuple (start_time, end_time, suggested_users_count)
    """
    segments = []
    
    # Calcola la durata totale in ore
    start_hour = coverage.start_time.hour + coverage.start_time.minute / 60.0
    end_hour = coverage.end_time.hour + coverage.end_time.minute / 60.0
    
    # Se la copertura attraversa la mezzanotte
    if end_hour < start_hour:
        end_hour += 24
    
    total_duration = end_hour - start_hour
    
    # LIMITE MASSIMO ASSOLUTO: 8 ore per turno
    MAX_SHIFT_HOURS = 8.0
    
    # DEBUG: Mostra sempre il calcolo - usando stderr per essere sicuro che arrivi
    import sys
    print(f"SPLIT DEBUG: Copertura {coverage.start_time}-{coverage.end_time}, durata: {total_duration}h", file=sys.stderr, flush=True)
    
    # Se la durata è <= 8 ore, nessuna divisione necessaria
    if total_duration <= MAX_SHIFT_HOURS:
        print(f"SPLIT DEBUG: Durata {total_duration}h <= {MAX_SHIFT_HOURS}h, nessuna divisione necessaria")
        segments.append((coverage.start_time, coverage.end_time, 1))
        return segments
    
    print(f"SPLIT DEBUG: Durata {total_duration}h > {MAX_SHIFT_HOURS}h, divisione necessaria!")
    
    # Calcola quanti utenti servono per coprire la durata (sempre basato su MAX 8 ore)
    users_needed = int(total_duration / MAX_SHIFT_HOURS)
    if total_duration % MAX_SHIFT_HOURS > 0:
        users_needed += 1
    
    print(f"SPLIT DEBUG: Servono {users_needed} utenti per coprire {total_duration}h")
    
    # Calcola la durata ottimale per segmento distribuendo equamente
    segment_duration = total_duration / users_needed
    print(f"SPLIT DEBUG: Durata per segmento: {segment_duration}h")
    
    # Crea i segmenti bilanciati
    current_hour = start_hour
    
    for i in range(users_needed):
        if i == users_needed - 1:
            # Ultimo segmento: usa tutto il tempo rimanente
            segment_end_hour = end_hour
        else:
            # Segmenti intermedi: usa la durata calcolata e arrotonda alla mezz'ora
            raw_segment_end = current_hour + segment_duration
            segment_end_hour = round_to_half_hour(raw_segment_end)
            
            # Assicurati che non superi l'orario di fine
            if segment_end_hour >= end_hour - 0.5:
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
        
        segments.append((start_time_obj, end_time_obj, 1))
        print(f"SPLIT DEBUG: Segmento {i+1}: {start_time_obj}-{end_time_obj} ({segment_end_hour - current_hour}h)")
        current_hour = segment_end_hour
    
    print(f"SPLIT DEBUG: Creati {len(segments)} segmenti totali")
    return segments

def split_coverage_into_max_7h_segments(coverage):
    """
    DEPRECATA: Usa split_coverage_into_segments_by_user_capacity() invece.
    Mantenuta per compatibilità con codice esistente.
    """
    MAX_CONSECUTIVE_HOURS = 8  # Aumentato a 8h per una giornata lavorativa completa
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
    - Smart user capacity-based shift splitting (automatic division based on part-time %)
    - Intelligent rest period management (prevents inappropriate consecutive shifts)
    - Weekly rest compliance (minimum 2 days off per week)
    - Weekly hours compliance (40h base for 100%, proportional for part-time)
    
    Bilanciamento: L'algoritmo favorisce gli utenti con minor utilizzo percentuale 
    nei 30 giorni precedenti, bilanciando automaticamente il carico di lavoro.
    
    Divisione Intelligente: Coperture che eccedono l'orario lavorativo disponibile 
    degli utenti (8h per 100%, proporzionale per part-time) vengono automaticamente 
    divise su più utenti per ottimizzare la distribuzione del carico.
    
    Gestione Riposo: Sistema previene assegnazioni consecutive inappropriate come 
    turno notturno seguito da turno mattutino, garantendo adeguati periodi di riposo.
    
    Compliance Settimanale: Garantisce almeno 2 giorni di riposo settimanali e 
    rispetto del limite di 40 ore settimanali (proporzionale per part-time).
    """
    # DEBUG: Aggiungo logging all'inizio per verificare che la funzione venga chiamata
    import sys
    print(f"FUNCTION DEBUG: generate_shifts_for_period chiamata per periodo {start_date} - {end_date}", file=sys.stderr, flush=True)
    
    # Get all active coverage configurations valid for the period
    coverage_configs = PresidioCoverage.query.filter(
        PresidioCoverage.active == True,
        PresidioCoverage.start_date <= end_date,
        PresidioCoverage.end_date >= start_date
    ).all()
    
    if not coverage_configs:
        return False, "Nessuna copertura presidio valida per il periodo selezionato. Configura prima i requisiti di copertura per le date richieste."
    
    # Get all eligible users (excluding administrators, and only those with special "Turni" work schedule)
    # Note: "Turni" is different from normal schedules like "Orario per sede Turni" - only "Turni" users are eligible for automatic shift generation
    all_users = User.query.join(WorkSchedule, User.work_schedule_id == WorkSchedule.id, isouter=True).filter(
        User.active == True,
        User.role != 'Amministratore',
        WorkSchedule.name == 'Turni'  # Only the special "Turni" schedule type
    ).all()
    
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
            
            # Split coverage into segments based on user capacity
            # Prima ottieni gli utenti disponibili per questa copertura
            coverage_required_roles = coverage.get_required_roles_list() if hasattr(coverage, 'get_required_roles_list') else []
            coverage_available_users = []
            
            for role in coverage_required_roles:
                if role in users_by_role:
                    for user in users_by_role[role]:
                        if (user.id not in user_leave_dates or 
                            current_date not in user_leave_dates[user.id]):
                            coverage_available_users.append(user)
            
            # Se non ci sono ruoli specifici, usa tutti gli utenti disponibili
            if not coverage_available_users:
                for user in all_users:
                    if (user.id not in user_leave_dates or 
                        current_date not in user_leave_dates[user.id]):
                        coverage_available_users.append(user)
            
            # Dividi la copertura basandoti sulla capacità degli utenti
            import sys
            print(f"MAIN DEBUG: Processando copertura {coverage.start_time}-{coverage.end_time}", file=sys.stderr, flush=True)
            coverage_segments = split_coverage_into_segments_by_user_capacity(coverage, coverage_available_users)
            print(f"MAIN DEBUG: Ricevuti {len(coverage_segments)} segmenti", file=sys.stderr, flush=True)
            
            # DEBUG: Verifica che i segmenti siano corretti
            total_coverage_hours = get_shift_duration_hours(coverage.start_time, coverage.end_time)
            if total_coverage_hours > 8.0:
                print(f"DEBUG: Copertura originale {coverage.start_time}-{coverage.end_time} ({total_coverage_hours}h) divisa in {len(coverage_segments)} segmenti:")
                for i, (seg_start, seg_end, users_count) in enumerate(coverage_segments):
                    seg_hours = get_shift_duration_hours(seg_start, seg_end)
                    print(f"  Segmento {i+1}: {seg_start}-{seg_end} ({seg_hours}h)")
                    if seg_hours > 8.0:
                        print(f"  ERRORE: Segmento ancora troppo lungo!")
            
            # Se un segmento è ancora troppo lungo, applicare split ricorsivo
            final_segments = []
            for segment_start, segment_end, users_count in coverage_segments:
                segment_hours = get_shift_duration_hours(segment_start, segment_end)
                if segment_hours > 8.0:
                    print(f"ERRORE: Segmento {segment_start}-{segment_end} ancora {segment_hours}h, riapplicando split...")
                    # Crea una mini-copertura per questo segmento e riapplica lo split
                    mini_coverage = type(coverage)()
                    for attr in ['id', 'day_of_week', 'description', 'required_roles', 'role_count', 'active', 'valid_from', 'valid_to']:
                        if hasattr(coverage, attr):
                            setattr(mini_coverage, attr, getattr(coverage, attr))
                    mini_coverage.start_time = segment_start
                    mini_coverage.end_time = segment_end
                    
                    # Riapplica split ricorsivamente
                    sub_segments = split_coverage_into_segments_by_user_capacity(mini_coverage, coverage_available_users)
                    final_segments.extend(sub_segments)
                else:
                    final_segments.append((segment_start, segment_end, users_count))
            
            coverage_segments = final_segments
            
            for segment_start, segment_end, users_count in coverage_segments:
                slot_key = (segment_start.strftime('%H:%M'), segment_end.strftime('%H:%M'))
                if slot_key not in time_slot_groups:
                    time_slot_groups[slot_key] = []
                # Crea una copia della copertura con gli orari del segmento per evitare sovrapposizioni
                segment_coverage = type(coverage)()
                for attr in ['id', 'day_of_week', 'description', 'required_roles', 'role_count', 'active', 'valid_from', 'valid_to']:
                    if hasattr(coverage, attr):
                        setattr(segment_coverage, attr, getattr(coverage, attr))
                segment_coverage.start_time = segment_start
                segment_coverage.end_time = segment_end
                time_slot_groups[slot_key].append(segment_coverage)
        
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
                    # Enhanced bilanciamento: considera turni precedenti per evitare assegnazioni consecutive inappropriate
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
                        
                        # NUOVO: Penalità completa per turni consecutivi, riposo settimanale e ore settimanali
                        rest_penalty = get_rest_period_penalty(user.id, current_date, segment_start, segment_end)
                        
                        # Primary: bonus sottoutilizzo, Secondary: penalità riposo/compliance, Tertiary: gap personale, Quaternary: utilizzo corrente basso
                        return (-underutilization_bonus, rest_penalty, -role_gap, -personal_gap, current_util)
                    
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
                        # Sort by current utilization AND full compliance penalties (lowest first)
                        def get_fallback_score(user):
                            current_util = current_utilization.get(user.id, 0)
                            full_penalty = get_rest_period_penalty(user.id, current_date, segment_start, segment_end)
                            return (full_penalty, current_util)
                        
                        final_fallback.sort(key=get_fallback_score)
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
                    
                    # CONTROLLO CRITICO: Verifica che il turno non superi i limiti dell'utente
                    user_max_hours = get_user_max_daily_hours(selected_user)
                    
                    if segment_hours > user_max_hours:
                        # ERRORE: Questo turno supera il limite dell'utente, non dovrebbe succedere
                        # Se succede, significa che la funzione split non ha funzionato correttamente
                        # Forza la divisione del turno qui
                        print(f"ERRORE: Turno di {segment_hours}h supera limite {user_max_hours}h per utente {selected_user.username}")
                        print(f"Turno: {segment_start} - {segment_end}")
                        continue  # Salta questo turno troppo lungo
                    
                    # CRITICO: Verifica durata prima di creare il turno
                    segment_duration = get_shift_duration_hours(segment_start, segment_end)
                    if segment_duration > 8.0:
                        import sys
                        print(f"ERRORE CRITICO: Tentativo di creare turno di {segment_duration}h ({segment_start}-{segment_end}) per {selected_user.nome} {selected_user.cognome}!", file=sys.stderr, flush=True)
                        print(f"ERRORE CRITICO: Interrotto per prevenire turno illegale!", file=sys.stderr, flush=True)
                        continue  # Skip this segment, don't create illegal shift
                    
                    # DEBUG: Log della creazione turno
                    import sys  
                    print(f"TURNO DEBUG: Creando turno {segment_start}-{segment_end} ({segment_duration}h) per {selected_user.nome} {selected_user.cognome}", file=sys.stderr, flush=True)
                    
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


def generate_reperibilita_shifts_from_coverage(coverage_period, start_date, end_date, created_by_id):
    """
    Genera turni di reperibilità basati su una copertura esistente selezionata
    """
    from models import User, ReperibilitaCoverage, ReperibilitaShift, LeaveRequest, WorkSchedule
    from app import db
    from datetime import timedelta
    from collections import defaultdict
    
    # Parse il period_key per ottenere le date della copertura - formato: start_date__end_date__sede_key
    try:
        parts = coverage_period.split('__')
        coverage_start = parts[0]
        coverage_end = parts[1]
        sede_key = parts[2] if len(parts) > 2 else None
        coverage_start_date = datetime.strptime(coverage_start, '%Y-%m-%d').date()
        coverage_end_date = datetime.strptime(coverage_end, '%Y-%m-%d').date()
    except:
        return 0, ["Errore nel formato della copertura selezionata"]
    
    # Ottieni tutte le coperture per il periodo selezionato, filtrando per sede se specificata
    query = ReperibilitaCoverage.query.filter(
        ReperibilitaCoverage.active == True,
        ReperibilitaCoverage.start_date == coverage_start_date,
        ReperibilitaCoverage.end_date == coverage_end_date
    )
    
    # Se c'è una sede specifica nel period_key, filtra per quella sede
    if sede_key and sede_key != "no_sede":
        sede_ids = [int(sid) for sid in sede_key.split('_')]
        # Filtra coperture che hanno almeno una delle sedi specificate
        coverages = []
        for coverage in query.all():
            coverage_sede_ids = coverage.get_sedi_ids_list()
            if any(sid in coverage_sede_ids for sid in sede_ids):
                coverages.append(coverage)
    else:
        coverages = query.all()
    
    if not coverages:
        return 0, ["Nessuna copertura trovata per il periodo selezionato"]
    
    # Ottieni utenti attivi escludendo amministratori
    # Per reperibilità, includiamo tutti gli operatori attivi indipendentemente dall'orario
    all_users = User.query.filter(
        User.active == True,
        User.role != 'Amministratore'
    ).all()
    
    users_by_role = defaultdict(list)
    for user in all_users:
        users_by_role[user.role].append(user)
    
    # Ottieni le richieste di ferie per il periodo
    leave_requests = LeaveRequest.query.filter(
        LeaveRequest.status.in_(['Pending', 'Approved']),
        LeaveRequest.start_date <= end_date,
        LeaveRequest.end_date >= start_date
    ).all()
    
    # Mappa delle date di ferie per utente
    user_leave_dates = defaultdict(set)
    for leave in leave_requests:
        current_date = max(leave.start_date, start_date)
        while current_date <= min(leave.end_date, end_date):
            user_leave_dates[leave.user_id].add(current_date)
            current_date += timedelta(days=1)
    
    # Calcola utilizzazione attuale per bilanciamento
    current_utilization = defaultdict(float)
    
    shifts_created = 0
    warnings = []
    
    # Genera turni giorno per giorno
    current_date = start_date
    while current_date <= end_date:
        day_of_week = current_date.weekday()  # 0=Monday, 6=Sunday
        
        # Trova coperture per questo giorno della settimana
        day_coverages = [c for c in coverages if c.day_of_week == day_of_week]
        
        for coverage in day_coverages:
            # Ottieni ruoli richiesti per questa copertura
            required_roles = coverage.get_required_roles_list()
            if not required_roles:
                continue
            
            # Ottieni sedi per questa copertura
            coverage_sedi = coverage.get_sedi_ids_list()
            
            # Per ogni ruolo richiesto, assegna un utente
            for required_role in required_roles:
                eligible_users = users_by_role.get(required_role, [])
                
                if not eligible_users:
                    warnings.append(f"Nessun utente con ruolo {required_role} disponibile")
                    continue
                
                # Filtra utenti che sono nella sede giusta (se specificata)
                if coverage_sedi:
                    eligible_users = [u for u in eligible_users if u.sede_id in coverage_sedi]
                
                # Filtra utenti non in ferie
                available_users = [
                    user for user in eligible_users
                    if user.id not in user_leave_dates or current_date not in user_leave_dates[user.id]
                ]
                
                if not available_users:
                    sede_names = coverage.get_sedi_names()
                    warnings.append(f"Nessun {required_role} disponibile il {current_date.strftime('%d/%m/%Y')} per {sede_names}")
                    continue
                
                # Ordina per utilizzazione corrente (bilanciamento)
                available_users.sort(key=lambda u: current_utilization[u.id])
                
                selected_user = available_users[0]
                
                # Crea il turno di reperibilità
                shift = ReperibilitaShift()
                shift.user_id = selected_user.id
                shift.date = current_date
                shift.start_time = coverage.start_time
                shift.end_time = coverage.end_time
                shift.description = coverage.description or f"Reperibilità {required_role}"
                shift.created_by = created_by_id
                
                db.session.add(shift)
                shifts_created += 1
                
                # Aggiorna utilizzazione per bilanciamento
                shift_hours = (coverage.end_time.hour - coverage.start_time.hour) + \
                             (coverage.end_time.minute - coverage.start_time.minute) / 60
                current_utilization[selected_user.id] += shift_hours
        
        current_date += timedelta(days=1)
    
    return shifts_created, warnings


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
            pass  # Silent error handling
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
        pass  # Silent error handling
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
        # Active users (excluding protected/administrative roles)
        from config import get_config
        config = get_config()
        active_users = User.query.filter(User.active.is_(True)).filter(~User.role.in_(config.EXCLUDED_ROLES_FROM_REPORTS)).count()
        
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
        
        # Calculate role-based statistics - show ALL active roles, even with 0 users
        from models import UserRole
        
        # Get all active roles first
        active_roles = UserRole.query.filter_by(active=True).all()
        
        # Initialize all roles with 0 count
        role_stats = {}
        for role in active_roles:
            role_stats[role.name] = 0
        
        # Count users by role
        all_active_users = User.query.filter(User.active.is_(True)).all()
        for user in all_active_users:
            # Only count if the role is active
            if user.role in role_stats:
                role_stats[user.role] += 1
        
        # Creo un oggetto con attributi per compatibilità template dashboard
        class TeamStats:
            def __init__(self, total_users, user_counts_by_role, active_users, total_hours, pending_leaves):
                self.total_users = total_users
                self.user_counts_by_role = user_counts_by_role
                self.active_users = active_users
                self.total_hours = round(total_hours, 2)
                self.pending_leaves = pending_leaves
                self.avg_hours_per_user = round(total_hours / active_users if active_users > 0 else 0, 2)
                self.total_team_interventions = total_team_interventions
                self.completed_team_interventions = len(completed_team_interventions)
                self.active_team_interventions = active_team_interventions
                self.team_avg_resolution_time_minutes = round(team_avg_resolution_time, 1)
                self.total_team_intervention_hours = round(total_team_intervention_hours, 2)
                self.team_remote_interventions = team_remote_interventions
                self.team_onsite_interventions = team_onsite_interventions
                self.role_stats = role_stats
        
        return TeamStats(active_users, role_stats, active_users, estimated_hours, pending_leaves)
        
    except Exception as e:
        pass  # Silent error handling
        # Ritorna oggetto con attributi per evitare errori template
        class TeamStats:
            def __init__(self):
                self.total_users = 0
                self.user_counts_by_role = {}
                self.active_users = 0
                self.total_hours = 0
                self.pending_leaves = 0
                self.avg_hours_per_user = 0
                self.total_team_interventions = 0
                self.completed_team_interventions = 0
                self.active_team_interventions = 0
                self.team_avg_resolution_time_minutes = 0
                self.total_team_intervention_hours = 0
                self.team_remote_interventions = 0
                self.team_onsite_interventions = 0
                self.role_stats = {}
        
        return TeamStats()

def check_user_schedule_with_permissions(user_id, check_datetime=None):
    """
    Controlla gli orari di lavoro dell'utente basandosi sulla sede e sui permessi approvati.
    
    Args:
        user_id: ID dell'utente
        check_datetime: datetime da controllare (default: ora corrente)
        
    Returns:
        dict: {
            'has_schedule': bool,
            'schedule_info': dict,
            'entry_status': str,  # 'normale', 'ritardo', 'anticipo'
            'exit_status': str,   # 'normale', 'ritardo', 'anticipo'
            'message': str
        }
    """
    from models import User, WorkSchedule, LeaveRequest
    from datetime import datetime, time, timedelta
    
    if not check_datetime:
        from zoneinfo import ZoneInfo
        italy_tz = ZoneInfo('Europe/Rome')
        check_datetime = datetime.now(italy_tz)
    
    check_date = check_datetime.date()
    check_time = check_datetime.time()
    
    # Ottieni l'utente e la sua sede
    user = User.query.get(user_id)
    if not user or not user.sede_id:
        return {
            'has_schedule': False,
            'schedule_info': None,
            'entry_status': 'normale',
            'exit_status': 'normale',
            'message': 'Utente non ha una sede assegnata'
        }
    
    # Trova l'orario di lavoro per la sede dell'utente
    # Controlla se è un giorno della settimana coperto dagli orari
    day_of_week = check_date.weekday()  # 0=Lunedì, 6=Domenica
    
    schedule = WorkSchedule.query.filter_by(
        sede_id=user.sede_id
    ).first()
    
    if not schedule:
        return {
            'has_schedule': False,
            'schedule_info': None,
            'entry_status': 'normale',
            'exit_status': 'normale',
            'message': 'Nessun orario di lavoro configurato per la sede'
        }
    
    # Controlla se questo giorno è coperto dall'orario
    days_of_week = schedule.get_days_of_week_list()
    if day_of_week not in days_of_week:
        return {
            'has_schedule': False,
            'schedule_info': None,
            'entry_status': 'normale',
            'exit_status': 'normale',
            'message': 'Giorno non lavorativo secondo l\'orario della sede'
        }
    
    # Orari base dalla sede
    base_start_time = schedule.start_time_min
    base_end_time = schedule.end_time_min
    
    # Controlla se ci sono permessi approvati per oggi
    approved_leaves = LeaveRequest.query.filter(
        LeaveRequest.user_id == user_id,
        LeaveRequest.status == 'Approved',
        LeaveRequest.start_date <= check_date,
        LeaveRequest.end_date >= check_date
    ).all()
    
    # Calcola gli orari effettivi considerando i permessi
    effective_start_time = base_start_time
    effective_end_time = base_end_time
    
    for leave in approved_leaves:
        if leave.leave_type == 'Permesso':
            # Per i permessi, assumiamo che siano orari (es. 9:00-11:00)
            # Se il permesso copre l'inizio della giornata, sposta l'orario di entrata
            if hasattr(leave, 'start_time') and hasattr(leave, 'end_time'):
                # Se il permesso inizia dall'orario di lavoro, sposta l'entrata
                if leave.start_time <= base_start_time:
                    effective_start_time = leave.end_time
    
    # Calcola lo stato di entrata/uscita
    entry_status = 'normale'
    exit_status = 'normale'
    
    # Tolleranza: 15 minuti per l'entrata, 5 minuti per l'uscita
    entry_tolerance = timedelta(minutes=15)
    exit_tolerance = timedelta(minutes=5)
    
    # Converti i tempi in datetime per il confronto con timezone italiana
    from zoneinfo import ZoneInfo
    italy_tz = ZoneInfo('Europe/Rome')
    
    effective_start_datetime = datetime.combine(check_date, effective_start_time).replace(tzinfo=italy_tz)
    effective_end_datetime = datetime.combine(check_date, effective_end_time).replace(tzinfo=italy_tz)
    
    # Assicurati che check_datetime abbia timezone
    if check_datetime.tzinfo is None:
        check_datetime = check_datetime.replace(tzinfo=italy_tz)
    
    # Controlla lo stato di entrata
    if check_time <= effective_start_time:
        entry_status = 'anticipo'
    elif check_datetime > effective_start_datetime + entry_tolerance:
        entry_status = 'ritardo'
    else:
        entry_status = 'normale'
    
    # Controlla lo stato di uscita
    if check_time < effective_end_time:
        exit_status = 'anticipo'
    elif check_datetime > effective_end_datetime + exit_tolerance:
        exit_status = 'straordinario'
    else:
        exit_status = 'normale'
    
    schedule_info = {
        'sede_name': user.sede_obj.name if user.sede_obj else 'Sconosciuta',
        'base_start_time': base_start_time.strftime('%H:%M'),
        'base_end_time': base_end_time.strftime('%H:%M'),
        'effective_start_time': effective_start_time.strftime('%H:%M'),
        'effective_end_time': effective_end_time.strftime('%H:%M'),
        'has_permissions': len(approved_leaves) > 0,
        'permissions': [{'type': l.leave_type, 'reason': l.reason} for l in approved_leaves]
    }
    
    return {
        'has_schedule': True,
        'schedule_info': schedule_info,
        'entry_status': entry_status,
        'exit_status': exit_status,
        'message': None
    }


def generate_reperibilita_shifts(start_date, end_date, created_by_id):
    """
    Genera turni di reperibilità basati sulle coperture definite
    """
    from models import User, ReperibilitaCoverage, ReperibilitaShift, LeaveRequest, WorkSchedule
    from app import db
    import json
    from datetime import timedelta
    from collections import defaultdict
    
    # Get all users grouped by role (excluding administrators, and only those with special "Turni" work schedule)
    # Note: "Turni" is different from normal schedules like "Orario per sede Turni" - only "Turni" users are eligible for automatic shift generation
    all_users = User.query.join(WorkSchedule, User.work_schedule_id == WorkSchedule.id, isouter=True).filter(
        User.active == True,
        User.role != 'Amministratore',
        WorkSchedule.name == 'Turni'  # Only the special "Turni" schedule type
    ).all()
    
    users_by_role = defaultdict(list)
    for user in all_users:
        users_by_role[user.role].append(user)
    
    # Get coverage configurations for the time period
    coverage_configs = ReperibilitaCoverage.query.filter(
        ReperibilitaCoverage.active == True
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
            
            # If no users available from required roles, expand to all active users with "Turni" schedule to ensure coverage
            if not available_users:
                fallback_users = User.query.join(WorkSchedule, User.work_schedule_id == WorkSchedule.id, isouter=True).filter(
                    User.active == True,
                    User.role != 'Amministratore',
                    WorkSchedule.name == 'Turni'
                ).all()
                
                available_users = [
                    user for user in fallback_users 
                    if user.id not in user_leave_dates or current_date not in user_leave_dates[user.id]
                ]
            
            # Filter based on reperibilità capacity (independent from presidio shifts)
            preferred_users = [user for user in available_users if should_assign_reperibilita_shift(user, current_date, current_utilization.get(user.id, 0))]
            
            # If no preferred users, use all available users to ensure coverage
            final_available_users = preferred_users if preferred_users else available_users
            
            if final_available_users:
                # Sort by priority for reperibilità assignment with rest period management
                def get_reperibilita_priority_score(user):
                    # Use current utilization plus full compliance penalties
                    current_util = current_utilization.get(user.id, 0)
                    full_penalty = get_rest_period_penalty(user.id, current_date, coverage.start_time, coverage.end_time)
                    
                    # Combina utilizzo corrente e penalità compliance per priorità intelligente
                    return (full_penalty, current_util)
                
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

def send_leave_request_message(leave_request, action_type, sender_user=None):
    """Invia messaggi automatici per le richieste di ferie/permessi
    
    Args:
        leave_request: Oggetto LeaveRequest
        action_type: 'created', 'cancelled', 'approved', 'rejected'  
        sender_user: Utente che ha eseguito l'azione (per cancelled è l'utente stesso)
    """
    from models import InternalMessage, User
    pass  # Leave request messages
    
    # Determina i destinatari in base al tipo di azione
    recipients = []
    
    if action_type in ['created', 'cancelled']:
        # Trova tutti gli utenti che possono approvare richieste
        # Filtra per sede: stesso sede_id o all_sedi=True
        all_users = User.query.filter_by(active=True).all()
        
        for user in all_users:
            # Controlla se l'utente può approvare richieste
            if hasattr(user, 'can_approve_leave') and user.can_approve_leave():
                # Controlla appartenenza sede
                if (user.all_sedi or  # Accesso a tutte le sedi
                    (user.sede_id and leave_request.user.sede_id and 
                     user.sede_id == leave_request.user.sede_id)):  # Stessa sede
                    recipients.append(user)
                    pass  # Approver added
        
        pass  # Recipients processed
        
        # Rimuovi duplicati e l'utente richiedente se presente
        recipients = list(set(recipients))
        if leave_request.user in recipients:
            recipients.remove(leave_request.user)
            
    elif action_type in ['approved', 'rejected']:
        # Per approvazioni e rifiuti, invia messaggio solo all'utente richiedente
        recipients = [leave_request.user]
    
    # Determina titolo e messaggio in base all'azione
    if action_type == 'created':
        title = f"Nuova richiesta {leave_request.leave_type.lower()}"
        message = f"{leave_request.user.get_full_name()} ha richiesto {leave_request.leave_type.lower()} dal {leave_request.start_date.strftime('%d/%m/%Y')} al {leave_request.end_date.strftime('%d/%m/%Y')}"
        if leave_request.reason:
            message += f"\nMotivo: {leave_request.reason}"
        msg_type = 'info'
        
    elif action_type == 'cancelled':
        title = f"Richiesta {leave_request.leave_type.lower()} cancellata"
        message = f"{leave_request.user.get_full_name()} ha cancellato la sua richiesta di {leave_request.leave_type.lower()} ({leave_request.start_date.strftime('%d/%m/%Y')} - {leave_request.end_date.strftime('%d/%m/%Y')})"
        msg_type = 'warning'
    
    elif action_type == 'approved':
        title = f"Richiesta {leave_request.leave_type.lower()} approvata"
        message = f"La tua richiesta di {leave_request.leave_type.lower()} dal {leave_request.start_date.strftime('%d/%m/%Y')} al {leave_request.end_date.strftime('%d/%m/%Y')} è stata approvata"
        if sender_user:
            message += f" da {sender_user.get_full_name()}"
        msg_type = 'success'
    
    elif action_type == 'rejected':
        title = f"Richiesta {leave_request.leave_type.lower()} rifiutata"
        message = f"La tua richiesta di {leave_request.leave_type.lower()} dal {leave_request.start_date.strftime('%d/%m/%Y')} al {leave_request.end_date.strftime('%d/%m/%Y')} è stata rifiutata"
        if sender_user:
            message += f" da {sender_user.get_full_name()}"
        msg_type = 'danger'
    
    # Crea i messaggi per tutti i destinatari
    for recipient in recipients:
        internal_msg = InternalMessage(
            recipient_id=recipient.id,
            sender_id=sender_user.id if sender_user else None,
            title=title,
            message=message,
            message_type=msg_type,
            related_leave_request_id=leave_request.id
        )
        db.session.add(internal_msg)
    
    try:
        db.session.commit()
        pass  # Messages sent
    except Exception as e:
        pass  # Silent error handling
        db.session.rollback()


def send_overtime_request_message(overtime_request, action_type, sender_user=None):
    """Invia messaggi automatici per le richieste di straordinario
    
    Args:
        overtime_request: Oggetto OvertimeRequest
        action_type: 'created', 'cancelled', 'approved', 'rejected'  
        sender_user: Utente che ha eseguito l'azione (per cancelled è l'utente stesso)
    """
    from models import InternalMessage, User
    
    pass  # Overtime request messages
    
    try:
        # Determina i destinatari in base al tipo di azione
        recipients = []
        
        if action_type in ['created', 'cancelled']:
            # Trova tutti gli utenti che possono approvare richieste straordinari
            # Filtra per sede: stesso sede_id o all_sedi=True
            all_users = User.query.filter_by(active=True).all()
            
            for user in all_users:
                # Controlla se l'utente può approvare richieste
                if hasattr(user, 'can_approve_overtime_requests') and user.can_approve_overtime_requests():
                    # Controlla appartenenza sede
                    if (user.all_sedi or  # Accesso a tutte le sedi
                        (user.sede_id and overtime_request.employee.sede_id and 
                         user.sede_id == overtime_request.employee.sede_id)):  # Stessa sede
                        recipients.append(user)
                        pass  # Overtime approver added
            
            pass  # Overtime recipients processed
            
            # Rimuovi duplicati e l'utente richiedente se presente
            recipients = list(set(recipients))
            if overtime_request.employee in recipients:
                recipients.remove(overtime_request.employee)
                
        elif action_type in ['approved', 'rejected']:
            # Per approvazioni e rifiuti, invia messaggio solo all'utente richiedente
            recipients = [overtime_request.employee]
        
        # Determina titolo e messaggio in base all'azione
        if action_type == 'created':
            title = f"Nuova richiesta straordinario"
            message = f"{overtime_request.employee.get_full_name()} ha richiesto straordinario per il {overtime_request.overtime_date.strftime('%d/%m/%Y')} dalle {overtime_request.start_time.strftime('%H:%M')} alle {overtime_request.end_time.strftime('%H:%M')}"
            if overtime_request.motivation:
                message += f"\nMotivazione: {overtime_request.motivation}"
            message += f"\nTipologia: {overtime_request.overtime_type.name}"
            msg_type = 'info'
            
        elif action_type == 'cancelled':
            title = f"Richiesta straordinario cancellata"
            message = f"{overtime_request.employee.get_full_name()} ha cancellato la sua richiesta di straordinario del {overtime_request.overtime_date.strftime('%d/%m/%Y')}"
            msg_type = 'warning'
        
        elif action_type == 'approved':
            title = f"Richiesta straordinario approvata"
            message = f"La tua richiesta di straordinario del {overtime_request.overtime_date.strftime('%d/%m/%Y')} è stata approvata"
            if overtime_request.approval_comment:
                message += f"\nCommento: {overtime_request.approval_comment}"
            msg_type = 'success'
            
        elif action_type == 'rejected':
            title = f"Richiesta straordinario rifiutata"
            message = f"La tua richiesta di straordinario del {overtime_request.overtime_date.strftime('%d/%m/%Y')} è stata rifiutata"
            if overtime_request.approval_comment:
                message += f"\nCommento: {overtime_request.approval_comment}"
            msg_type = 'danger'
        
        # Crea i messaggi per tutti i destinatari
        for recipient in recipients:
            internal_msg = InternalMessage(
                recipient_id=recipient.id,
                sender_id=sender_user.id if sender_user else overtime_request.employee.id,
                title=title,
                message=message,
                message_type=msg_type
            )
            db.session.add(internal_msg)
    
        try:
            db.session.commit()
            pass  # Overtime messages sent
        except Exception as e:
            pass  # Silent error handling
            db.session.rollback()
    
    except Exception as e:
        pass  # Silent error handling
        import traceback
        traceback.print_exc()
