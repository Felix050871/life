from datetime import datetime, timedelta, time
from models import PresidioCoverageTemplate, PresidioCoverage, Shift, User, WorkSchedule
import json
from app import db
from utils import split_coverage_into_segments_by_user_capacity

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
        
        
        # Ordina coperture per ORARIO CRONOLOGICO: prima turni mattutini, poi pomeridiani, poi serali
        # Questo è FONDAMENTALE per applicare correttamente le regole di riposo dopo turni notturni
        day_coverages.sort(key=lambda c: (c.start_time, c.end_time))
        
        for coverage in day_coverages:
            try:
                required_roles = json.loads(coverage.required_roles) if coverage.required_roles else []
                
                # Filtra utenti per ruolo richiesto
                role_users = [u for u in available_users if u.role in required_roles]
                
                # SPEZZAMENTO TURNI LUNGHI: Prima controlla se la copertura supera 8 ore
                shift_duration = calculate_shift_duration(coverage.start_time, coverage.end_time)
                
                if shift_duration > 8.0:
                    
                    # Spezza la copertura in segmenti da massimo 8 ore
                    segments = split_coverage_into_segments_by_user_capacity(coverage, role_users)
                    
                    # Processa ogni segmento separatamente
                    for segment_idx, (seg_start, seg_end, suggested_count) in enumerate(segments):
                        
                        # Verifica utenti idonei per questo segmento
                        eligible_users = []
                        for user in role_users:
                            if is_user_eligible_real_time(user.id, current_date, seg_start, seg_end, user_assignments):
                                eligible_users.append(user)
                        
                        
                        if not eligible_users:
                            # Segmento scoperto
                            uncovered_shift_info = {
                                'date': current_date,
                                'start_time': seg_start,
                                'end_time': seg_end,
                                'required_roles': required_roles,
                                'day_of_week': current_date.weekday()
                            }
                            uncovered_shifts.append(uncovered_shift_info)
                            continue
                        
                        # Seleziona miglior utente per questo segmento
                        selected_user = select_best_user_greedy(eligible_users, user_assignments, coverage)
                        
                        if selected_user:
                            # Verifica conflitti database per questo segmento
                            existing_segment_shift = Shift.query.filter(
                                Shift.user_id == selected_user.id,
                                Shift.date == current_date,
                                Shift.start_time == seg_start,
                                Shift.end_time == seg_end
                            ).first()
                            
                            if not existing_segment_shift:
                                # Crea turno per questo segmento
                                new_shift = Shift()
                                new_shift.user_id = selected_user.id
                                new_shift.date = current_date
                                new_shift.start_time = seg_start
                                new_shift.end_time = seg_end
                                new_shift.shift_type = 'presidio'
                                new_shift.created_by = created_by_user_id
                                db.session.add(new_shift)
                                turni_creati += 1
                                
                                # Traccia assegnamento segmento
                                user_assignments[selected_user.id].append((current_date, seg_start, seg_end))
                                
                else:
                    # Copertura <= 8 ore: logica normale
                    # Verifica in tempo reale i conflitti prima dell'assegnazione
                    eligible_users = []
                    for user in role_users:
                        if is_user_eligible_real_time(user.id, current_date, coverage.start_time, coverage.end_time, user_assignments):
                            eligible_users.append(user)
                    
                    
                    if not eligible_users:
                        # NESSUN UTENTE DISPONIBILE - TURNO SCOPERTO
                        uncovered_shift_info = {
                            'date': current_date,
                            'start_time': coverage.start_time,
                            'end_time': coverage.end_time,
                            'required_roles': required_roles,
                            'day_of_week': current_date.weekday()
                        }
                        uncovered_shifts.append(uncovered_shift_info)
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
                            
            
            except json.JSONDecodeError:
                continue
        
        current_date += timedelta(days=1)
    
    # Statistiche finali rimossi per pulizia codice
    
    # Report turni scoperti rimossi per pulizia codice
    
    return turni_creati, f"Creati {turni_creati} turni con algoritmo greedy ottimizzato ({len(uncovered_shifts)} turni scoperti)"

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
            # LOGICA CORRETTA: riconosce ENTRAMBI i turni notturni
            # - Turno mattutino notturno: 00:00-07:59 (inizia entro le 07:59)
            # - Turno serale notturno: 16:00-23:59 (finisce dalle 23:00 in poi)
            # IMPORTANTE: Il turno 08:00-16:00 NON è notturno!
            is_night_shift = (shift.start_time <= time(7, 59) or shift.end_time >= time(23, 0))
            if is_night_shift:
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
        # Turno notturno: LOGICA CORRETTA e SPECIFICA
        # - Turno mattutino notturno: inizia dalle 00:00 alle 07:59 (start_time <= 07:59)
        # - Turno serale notturno: finisce dalle 23:00 in poi (end_time >= 23:00)
        # IMPORTANTE: Il turno 08:00-16:00 NON è notturno!
        is_night_shift = (shift_start <= time(7, 59) or shift_end >= time(23, 0))
        
        if is_night_shift:
            # Calcola fine turno gestendo mezzanotte
            if shift_end <= shift_start:  # Attraversa mezzanotte
                shift_end_datetime = datetime.combine(shift_date + timedelta(days=1), shift_end)
            else:
                shift_end_datetime = datetime.combine(shift_date, shift_end)
            
            rest_end = shift_end_datetime + timedelta(hours=11)
            new_start_datetime = datetime.combine(date, start_time)
            
            if new_start_datetime < rest_end:
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