from datetime import datetime, timedelta
from models import PresidioCoverageTemplate, PresidioCoverage, Shift, User, WorkSchedule
import json
import sys
from app import db

def generate_shifts_methodical(template_id, start_date, end_date, created_by_user_id):
    """
    Approccio metodico per generazione turni 24/7 - MASSIMO 1 TURNO PER UTENTE PER GIORNO
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
    
    print(f"METHODICAL: Inizio generazione per {len(available_users)} utenti disponibili", file=sys.stderr, flush=True)
    
    # Tracciamento bilanciamento: utente -> numero turni assegnati
    user_shift_counts = {user.id: 0 for user in available_users}
    turni_creati = 0
    
    current_date = start_date
    while current_date <= end_date:
        day_of_week = current_date.weekday()
        day_coverages = [c for c in coverages if c.day_of_week == day_of_week]
        
        print(f"METHODICAL: Processo data {current_date}, {len(day_coverages)} coperture", file=sys.stderr, flush=True)
        
        # REGOLA FONDAMENTALE: MASSIMO 1 TURNO per utente per giorno
        daily_user_assignments = {}  # user_id -> (start_time, end_time)
        
        # Ordina coperture per orario per elaborazione sequenziale
        day_coverages.sort(key=lambda c: c.start_time)
        
        for coverage in day_coverages:
            try:
                required_roles = json.loads(coverage.required_roles) if coverage.required_roles else []
                
                # Filtra utenti per ruolo richiesto
                role_users = [u for u in available_users if u.role in required_roles]
                
                # IMPORTANTE: Escludi utenti già assegnati oggi
                available_for_coverage = [u for u in role_users if u.id not in daily_user_assignments]
                
                print(f"METHODICAL: Copertura {coverage.start_time}-{coverage.end_time}, ruoli {required_roles}, {len(available_for_coverage)}/{len(role_users)} utenti disponibili", file=sys.stderr, flush=True)
                
                if not available_for_coverage:
                    print(f"METHODICAL: NESSUN utente disponibile per {coverage.start_time}-{coverage.end_time}", file=sys.stderr, flush=True)
                    continue
                
                # Ordina utenti per numero turni assegnati (bilanciamento)
                available_for_coverage.sort(key=lambda u: user_shift_counts[u.id])
                
                # Seleziona il numero di utenti richiesto (max disponibili)
                users_to_assign = available_for_coverage[:min(coverage.role_count, len(available_for_coverage))]
                
                for user in users_to_assign:
                    # Verifica che non ci siano conflitti nel database
                    existing_shift = Shift.query.filter_by(
                        user_id=user.id,
                        date=current_date
                    ).first()
                    
                    if existing_shift:
                        print(f"METHODICAL: User {user.username} ha già turno in database, SKIP", file=sys.stderr, flush=True)
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
                    
                    # CRITICO: Traccia assegnamento giornaliero - BLOCCA altri turni
                    daily_user_assignments[user.id] = (coverage.start_time, coverage.end_time)
                    
                    # Aggiorna contatore bilanciamento
                    user_shift_counts[user.id] += 1
                    
                    print(f"METHODICAL: User {user.username} assegnato {coverage.start_time}-{coverage.end_time}, totale turni: {user_shift_counts[user.id]}", file=sys.stderr, flush=True)
            
            except json.JSONDecodeError:
                continue
        
        current_date += timedelta(days=1)
    
    # Statistiche finali
    for user in available_users:
        print(f"STATS: User {user.username} -> {user_shift_counts[user.id]} turni totali", file=sys.stderr, flush=True)
    
    return turni_creati, f"Creati {turni_creati} turni con approccio metodico 24/7"