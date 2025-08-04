from datetime import datetime, timedelta, time
from models import PresidioCoverageTemplate, PresidioCoverage, Shift, User, WorkSchedule
import json
import sys
import random
from app import db

def generate_shifts_advanced(template_id, start_date, end_date, created_by_user_id):
    """
    Sistema avanzato di generazione turni con regole rigorose di sicurezza operativa
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
    
    print(f"ADVANCED: Inizio generazione per {len(available_users)} utenti con regole rigorose", file=sys.stderr, flush=True)
    
    # Tracciamento storico degli assegnamenti per applicare regole
    user_assignments = {}  # user_id -> [(date, start_time, end_time), ...]
    for user in available_users:
        user_assignments[user.id] = []
    
    turni_creati = 0
    current_date = start_date
    
    while current_date <= end_date:
        day_of_week = current_date.weekday()
        day_coverages = [c for c in coverages if c.day_of_week == day_of_week]
        
        print(f"ADVANCED: Processo data {current_date}, {len(day_coverages)} coperture", file=sys.stderr, flush=True)
        
        # Ordina coperture per orario per elaborazione sequenziale
        day_coverages.sort(key=lambda c: c.start_time)
        
        for coverage in day_coverages:
            try:
                required_roles = json.loads(coverage.required_roles) if coverage.required_roles else []
                
                # Filtra utenti per ruolo richiesto
                role_users = [u for u in available_users if u.role in required_roles]
                
                # Applica tutte le regole di sicurezza per ogni utente
                eligible_users = []
                for user in role_users:
                    if is_user_eligible_for_shift(user.id, current_date, coverage.start_time, coverage.end_time, user_assignments):
                        eligible_users.append(user)
                    else:
                        print(f"ADVANCED: User {user.username} NON IDONEO per {coverage.start_time}-{coverage.end_time} il {current_date}", file=sys.stderr, flush=True)
                
                print(f"ADVANCED: Copertura {coverage.start_time}-{coverage.end_time}, {len(eligible_users)}/{len(role_users)} utenti idonei", file=sys.stderr, flush=True)
                
                if not eligible_users:
                    print(f"ADVANCED: NESSUN utente idoneo per {coverage.start_time}-{coverage.end_time}", file=sys.stderr, flush=True)
                    continue
                
                # Calcola durata del turno in ore
                shift_duration = calculate_shift_duration(coverage.start_time, coverage.end_time)
                
                # Verifica se il turno necessita spezzamento
                if shift_duration > 8.0:  # Turno troppo lungo
                    users_needed = max(coverage.role_count, int(shift_duration / 8) + 1)
                    print(f"ADVANCED: Turno lungo {shift_duration}h, serve spezzamento su {users_needed} utenti", file=sys.stderr, flush=True)
                else:
                    users_needed = coverage.role_count
                
                # Ordina utenti per bilanciamento (meno turni assegnati)
                eligible_users.sort(key=lambda u: len(user_assignments[u.id]))
                
                # Seleziona utenti da assegnare (max disponibili)
                users_to_assign = eligible_users[:min(users_needed, len(eligible_users))]
                
                for user in users_to_assign:
                    # Verifica conflitti database
                    existing_shift = Shift.query.filter_by(
                        user_id=user.id,
                        date=current_date
                    ).first()
                    
                    if existing_shift:
                        print(f"ADVANCED: User {user.username} ha già turno in database, SKIP", file=sys.stderr, flush=True)
                        continue
                    
                    # Crea il turno
                    new_shift = Shift(
                        user_id=user.id,
                        date=current_date,
                        start_time=coverage.start_time,
                        end_time=coverage.end_time,
                        shift_type='presidio',
                        created_by=created_by_user_id
                    )
                    db.session.add(new_shift)
                    turni_creati += 1
                    
                    # Traccia assegnamento per regole future
                    user_assignments[user.id].append((current_date, coverage.start_time, coverage.end_time))
                    
                    print(f"ADVANCED: User {user.username} assegnato {coverage.start_time}-{coverage.end_time}, turni totali: {len(user_assignments[user.id])}", file=sys.stderr, flush=True)
            
            except json.JSONDecodeError:
                continue
        
        current_date += timedelta(days=1)
    
    # Statistiche finali
    for user in available_users:
        print(f"STATS: User {user.username} -> {len(user_assignments[user.id])} turni totali", file=sys.stderr, flush=True)
    
    return turni_creati, f"Creati {turni_creati} turni con sistema avanzato e regole rigorose"

def is_user_eligible_for_shift(user_id, date, start_time, end_time, user_assignments):
    """
    Verifica se un utente è idoneo per un turno applicando tutte le regole di sicurezza
    """
    user_shifts = user_assignments[user_id]
    
    # Regola 1: Non sovrapposizione - Un utente non può fare due turni nello stesso giorno
    for shift_date, shift_start, shift_end in user_shifts:
        if shift_date == date:
            print(f"RULE_VIOLATION: User {user_id} già assegnato il {date}", file=sys.stderr, flush=True)
            return False
    
    # Regola 2: Non turni consecutivi
    previous_day = date - timedelta(days=1)
    next_day = date + timedelta(days=1)
    
    for shift_date, shift_start, shift_end in user_shifts:
        # Se ha turno pomeridiano/serale ieri (16:00-24:00), non può fare turno oggi
        if shift_date == previous_day:
            if shift_start >= time(16, 0) or shift_end > time(20, 0):
                print(f"RULE_VIOLATION: User {user_id} ha turno pomeridiano/serale il {previous_day}, SKIP {date}", file=sys.stderr, flush=True)
                return False
        
        # Se fa turno oggi e va oltre le 20:00, non può fare turno domani mattina
        if shift_date == date and end_time > time(20, 0):
            for future_date, future_start, future_end in user_shifts:
                if future_date == next_day and future_start < time(12, 0):
                    print(f"RULE_VIOLATION: User {user_id} turno serale oggi -> no turno mattina domani", file=sys.stderr, flush=True)
                    return False
    
    # Regola 3: Riposo obbligatorio dopo turno notturno (11 ore minimo)
    for shift_date, shift_start, shift_end in user_shifts:
        # Controlla turni notturni precedenti
        if shift_start <= time(6, 0) or shift_end <= time(8, 0):  # Turno notturno
            # Calcola quando finisce il riposo obbligatorio
            shift_end_datetime = datetime.combine(shift_date, shift_end)
            rest_end = shift_end_datetime + timedelta(hours=11)
            
            new_start_datetime = datetime.combine(date, start_time)
            
            if new_start_datetime < rest_end:
                print(f"RULE_VIOLATION: User {user_id} in riposo obbligatorio fino alle {rest_end}", file=sys.stderr, flush=True)
                return False
    
    return True

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