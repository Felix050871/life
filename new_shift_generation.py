from datetime import datetime, timedelta, time
from models import PresidioCoverageTemplate, PresidioCoverage, Shift, User, WorkSchedule
import json
import sys
from app import db

def generate_shifts_advanced(template_id, start_date, end_date, created_by_user_id):
    """
    Sistema ottimizzato di generazione turni con algoritmo greedy e priorità
    """
    
    # Ottieni coperture del template
    coverages = PresidioCoverage.query.filter_by(
        template_id=template_id,
        active=True
    ).all()
    
    if not coverages:
        return 0, "Nessuna copertura configurata per il template"
    
    # Ottieni tutti gli utenti disponibili per turni
    available_users = User.query.join(WorkSchedule, User.work_schedule_id == WorkSchedule.id).filter(
        User.active.is_(True),
        WorkSchedule.name == 'Turni'
    ).all()
    
    if not available_users:
        return 0, "Nessun utente disponibile per i turni"
    
    print(f"OPTIMIZED: Inizio generazione per {len(available_users)} utenti con algoritmo greedy", file=sys.stderr, flush=True)
    
    # Lista per tracciare turni scoperti
    uncovered_shifts = []
    
    # Carica turni notturni esistenti dal database per riposo post-notte
    existing_night_shifts = load_existing_night_shifts(available_users, start_date)
    
    # Tracciamento storico degli assegnamenti per applicare regole
    user_assignments = {}  # user_id -> [(date, start_time, end_time), ...]
    for user in available_users:
        user_assignments[user.id] = []
    
    # Aggiungi turni notturni esistenti al tracciamento
    for user_id, shifts in existing_night_shifts.items():
        user_assignments[user_id].extend(shifts)
    
    turni_creati = 0
    current_date = start_date
    
    while current_date <= end_date:
        day_of_week = current_date.weekday()
        day_coverages = [c for c in coverages if c.day_of_week == day_of_week]
        
        print(f"OPTIMIZED: Processo data {current_date}, {len(day_coverages)} coperture", file=sys.stderr, flush=True)
        
        # Ordina coperture per PRIORITÀ: prima turni difficili da coprire
        day_coverages.sort(key=lambda c: get_coverage_priority(c, current_date, available_users, user_assignments))
        
        for coverage in day_coverages:
            try:
                required_roles = json.loads(coverage.required_roles) if coverage.required_roles else []
                
                # Filtra utenti per ruolo richiesto
                role_users = [u for u in available_users if u.role in required_roles]
                
                # Verifica in tempo reale i conflitti prima dell'assegnazione
                eligible_users = []
                for user in role_users:
                    if is_user_eligible_real_time(user.id, current_date, coverage.start_time, coverage.end_time, user_assignments):
                        eligible_users.append(user)
                
                print(f"OPTIMIZED: Copertura {coverage.start_time}-{coverage.end_time}, {len(eligible_users)}/{len(role_users)} utenti idonei", file=sys.stderr, flush=True)
                
                if not eligible_users:
                    # NESSUN UTENTE DISPONIBILE - TURNO SCOPERTO
                    uncovered_shift_info = {
                        'date': current_date,
                        'start_time': coverage.start_time,
                        'end_time': coverage.end_time,
                        'required_roles': required_roles,
                        'day_of_week': current_date.weekday()
                    }
                    print(f"⚠️ TURNO SCOPERTO: {current_date} {coverage.start_time}-{coverage.end_time} - Ruoli richiesti: {required_roles} - NESSUN UTENTE IDONEO", file=sys.stderr, flush=True)
                    continue
                
                # Algoritmo GREEDY: seleziona utente con meno turni e migliori preferenze
                selected_user = select_best_user_greedy(eligible_users, user_assignments, coverage)
                
                if selected_user:
                    # Verifica conflitti database
                    existing_shift = Shift.query.filter_by(
                        user_id=selected_user.id,
                        date=current_date
                    ).first()
                    
                    if not existing_shift:
                        # Crea il turno
                        new_shift = Shift()
                        new_shift.user_id = selected_user.id
                        new_shift.date = current_date
                        new_shift.start_time = coverage.start_time
                        new_shift.end_time = coverage.end_time
                        new_shift.shift_type = 'presidio'
                        new_shift.created_by = created_by_user_id
                        db.session.add(new_shift)
                        turni_creati += 1
                        
                        # Traccia assegnamento per regole future
                        user_assignments[selected_user.id].append((current_date, coverage.start_time, coverage.end_time))
                        
                        print(f"OPTIMIZED: User {selected_user.username} assegnato {coverage.start_time}-{coverage.end_time}, turni totali: {len(user_assignments[selected_user.id])}", file=sys.stderr, flush=True)
            
            except json.JSONDecodeError:
                continue
        
        current_date += timedelta(days=1)
    
    # Statistiche finali
    for user in available_users:
        print(f"STATS: User {user.username} -> {len(user_assignments[user.id])} turni totali", file=sys.stderr, flush=True)
    
    return turni_creati, f"Creati {turni_creati} turni con algoritmo greedy ottimizzato"

def load_existing_night_shifts(users, start_date):
    """
    Carica turni notturni esistenti dal database per gestire il riposo post-notte
    """
    existing_shifts = {}
    for user in users:
        existing_shifts[user.id] = []
        
        # Cerca turni notturni recenti nel database
        past_shifts = Shift.query.filter(
            Shift.user_id == user.id,
            Shift.date >= start_date - timedelta(days=7),
            Shift.date < start_date
        ).all()
        
        for shift in past_shifts:
            if shift.start_time <= time(6, 0) or shift.end_time <= time(8, 0):
                existing_shifts[user.id].append((shift.date, shift.start_time, shift.end_time))
    
    return existing_shifts

def get_coverage_priority(coverage, date, users, assignments):
    """
    Calcola priorità di una copertura - prima i turni più difficili da coprire
    """
    required_roles = json.loads(coverage.required_roles) if coverage.required_roles else []
    role_users = [u for u in users if u.role in required_roles]
    
    eligible_count = 0
    for user in role_users:
        if is_user_eligible_real_time(user.id, date, coverage.start_time, coverage.end_time, assignments):
            eligible_count += 1
    
    # Priorità inversa: meno utenti disponibili = priorità più alta (numero più basso)
    return eligible_count

def is_user_eligible_real_time(user_id, date, start_time, end_time, user_assignments):
    """
    Verifica in tempo reale se un utente è idoneo con controllo di conflitto ottimizzato
    """
    user_shifts = user_assignments[user_id]
    
    # Regola 1: Non sovrapposizione - Un utente non può fare due turni nello stesso giorno
    for shift_date, shift_start, shift_end in user_shifts:
        if shift_date == date:
            return False
    
    # Regola 2: Non turni consecutivi migliorata
    previous_day = date - timedelta(days=1)
    
    for shift_date, shift_start, shift_end in user_shifts:
        # Se ha turno pomeridiano/serale ieri, non può fare turno oggi
        if shift_date == previous_day:
            if shift_start >= time(16, 0) or shift_end > time(20, 0):
                return False
    
    # Regola 3: Riposo obbligatorio dopo turno notturno (11 ore minimo) CORRETTA
    for shift_date, shift_start, shift_end in user_shifts:
        # Turno notturno: inizia prima delle 06:00 O finisce dopo le 23:00 O attraversa la mezzanotte
        is_night_shift = (shift_start <= time(6, 0) or 
                         shift_end >= time(23, 0) or 
                         shift_end <= time(8, 0))  # Turno che attraversa mezzanotte
        
        if is_night_shift:
            # Calcola fine turno gestendo mezzanotte
            if shift_end <= shift_start:  # Attraversa mezzanotte
                shift_end_datetime = datetime.combine(shift_date + timedelta(days=1), shift_end)
            else:
                shift_end_datetime = datetime.combine(shift_date, shift_end)
            
            rest_end = shift_end_datetime + timedelta(hours=11)
            new_start_datetime = datetime.combine(date, start_time)
            
            if new_start_datetime < rest_end:
                print(f"REGOLA 3 VIOLATA: User {user_id} ha turno notturno {shift_date} {shift_start}-{shift_end}, riposo fino {rest_end}, nuovo turno {new_start_datetime}", file=sys.stderr, flush=True)
                return False
    
    return True

def select_best_user_greedy(eligible_users, user_assignments, coverage):
    """
    Algoritmo greedy per selezionare il miglior utente considerando:
    - Numero di turni già assegnati (bilanciamento)
    - Preferenze temporali (ignora per ora)
    """
    if not eligible_users:
        return None
    
    # Ordina per numero di turni (meno turni = priorità più alta)
    eligible_users.sort(key=lambda u: len(user_assignments[u.id]))
    
    # Seleziona il primo (quello con meno turni)
    return eligible_users[0]

def calculate_shift_duration(start_time, end_time):
    """
    Calcola la durata di un turno in ore, gestendo i turni che attraversano la mezzanotte
    """
    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute
    
    if end_minutes <= start_minutes:  # Attraversa mezzanotte
        duration_minutes = (24 * 60) - start_minutes + end_minutes
    else:
        duration_minutes = end_minutes - start_minutes
    
    return duration_minutes / 60.0