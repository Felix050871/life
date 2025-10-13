# =============================================================================
# BANCA ORE BLUEPRINT
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta, time
from sqlalchemy import and_, or_, func, distinct

# Application Imports
from app import db
from models import User, AttendanceEvent, OvertimeRequest, LeaveRequest, italian_now
from utils import format_hours
from utils_tenant import filter_by_company, set_company_on_create

# Create Blueprint
banca_ore_bp = Blueprint('banca_ore', __name__)

def calculate_overtime_from_attendance(user_id, work_date):
    """
    Calcola le ore di straordinario automatiche dalle presenze.
    Utilizza la regola dei 30 minuti: si considera straordinario dalla mezz'ora in su
    dall'orario di uscita standard o dopo le 8 ore se non ci sono orari definiti.
    
    Args:
        user_id: ID dell'utente
        work_date: Data di lavoro da analizzare
        
    Returns:
        float: Ore di straordinario accumulate (0.0 se nessuna)
    """
    user = filter_by_company(User.query, User).filter(User.id == user_id).first()
    if not user or not user.banca_ore_enabled:
        return 0.0
    
    # Verifica se l'utente ha già una richiesta di straordinario per questa data
    existing_overtime = filter_by_company(OvertimeRequest.query, OvertimeRequest).filter(
        OvertimeRequest.employee_id == user_id,
        OvertimeRequest.overtime_date == work_date
    ).first()
    
    if existing_overtime:
        # Se c'è già una richiesta manuale, non calcoliamo automaticamente
        return 0.0
    
    # Calcola ore lavorate dalla presenza
    daily_hours = AttendanceEvent.get_daily_work_hours(user_id, work_date)
    if daily_hours <= 0:
        return 0.0
    
    # Determina ore standard di lavoro per l'utente
    standard_hours = 8.0  # Default 8 ore
    
    if user.work_schedule and user.should_check_attendance_timing():
        # Se ha un orario definito, usa quello come base
        # TODO: Implementare logica per ottenere ore standard dal WorkSchedule
        standard_hours = 8.0  # Per ora manteniamo 8 ore
    
    # Applica la percentuale part-time
    if user.part_time_percentage and user.part_time_percentage < 100:
        standard_hours = standard_hours * (user.part_time_percentage / 100.0)
    
    # Calcola ore in eccesso
    overtime_hours = daily_hours - standard_hours
    
    # Applica la regola dei 30 minuti: sotto i 30 minuti non si considera straordinario
    if overtime_hours < 0.5:
        return 0.0
    
    # Arrotonda ai quarti d'ora (0.25h)
    overtime_hours = round(overtime_hours * 4) / 4
    
    return max(0.0, overtime_hours)

def calculate_banca_ore_balance(user_id):
    """
    Calcola il saldo completo della banca ore per un utente.
    
    Args:
        user_id: ID dell'utente
        
    Returns:
        dict: Dizionario con informazioni complete del wallet banca ore
    """
    user = filter_by_company(User.query, User).filter(User.id == user_id).first()
    if not user or not user.banca_ore_enabled:
        return None
    
    # Controlli di sicurezza sui tipi
    limite_max = float(user.banca_ore_limite_max or 40.0)
    periodo_mesi = int(user.banca_ore_periodo_mesi or 12)
    
    # Data limite per calcolare scadenze (x mesi fa)
    data_limite_scadenza = italian_now() - timedelta(days=30 * periodo_mesi)
    
    # 1. Calcola ore accumulate da presenze automatiche (straordinario non richiesto)
    # OTTIMIZZATO: Invece di loop giorno per giorno, usa query aggregate
    ore_accumulate_presenze = 0.0
    
    try:
        # Query ottimizzata: ottieni ore totali lavorate nel periodo
        from sqlalchemy import text
        
        # Calcola periodo di query (dal data_limite_scadenza ad oggi)
        start_date = data_limite_scadenza.date()
        end_date = date.today()
        
        # Query per ottenere giorni con ore lavorate nel periodo
        result = db.session.execute(
            text("""
                SELECT date, SUM(
                    CASE 
                        WHEN event_type = 'clock_in' THEN -EXTRACT(EPOCH FROM timestamp)/3600.0
                        WHEN event_type = 'clock_out' THEN EXTRACT(EPOCH FROM timestamp)/3600.0
                        ELSE 0
                    END
                ) as daily_hours
                FROM attendance_event 
                WHERE user_id = :user_id 
                AND date >= :start_date 
                AND date <= :end_date
                GROUP BY date
                HAVING COUNT(*) >= 2
            """),
            {"user_id": user_id, "start_date": start_date, "end_date": end_date}
        )
        
        # Calcola ore straordinario per ogni giorno (mantengo la logica business)
        standard_hours = 8.0
        if user.part_time_percentage and user.part_time_percentage < 100:
            standard_hours = standard_hours * (user.part_time_percentage / 100.0)
        
        for row in result:
            daily_hours = float(abs(row[1])) if row[1] else 0.0  # Converte esplicitamente a float
            if daily_hours > standard_hours + 0.5:  # Regola 30 minuti
                overtime = daily_hours - standard_hours
                overtime = round(overtime * 4) / 4  # Arrotonda ai quarti d'ora
                ore_accumulate_presenze += max(0.0, overtime)
                
    except Exception as e:
        # Fallback al calcolo precedente in caso di errore query
        print(f"Errore calcolo banca ore ottimizzato: {e}")
        ore_accumulate_presenze = 0.0
    
    # 2. Calcola ore accumulate da straordinari approvati e convertiti in banca ore
    ore_accumulate_straordinari = 0.0
    # TODO: Implementare logica per straordinari approvati convertiti in banca ore
    
    # 3. Calcola ore utilizzate tramite permessi/ferie con banca ore
    ore_utilizzate = 0.0
    
    try:
        # Query per ottenere ore utilizzate da richieste approvate con banca ore
        approved_leaves_with_banca_ore = filter_by_company(LeaveRequest.query, LeaveRequest).filter(
            LeaveRequest.user_id == user_id,
            LeaveRequest.status == 'Approved',
            LeaveRequest.use_banca_ore == True,
            LeaveRequest.banca_ore_hours_used.isnot(None),
            LeaveRequest.approved_at >= data_limite_scadenza
        ).all()
        
        # Somma le ore effettivamente utilizzate
        for leave_request in approved_leaves_with_banca_ore:
            ore_utilizzate += leave_request.banca_ore_hours_used or 0.0
            
    except Exception as e:
        print(f"Errore calcolo ore utilizzate banca ore: {e}")
        ore_utilizzate = 0.0
    
    # Totali
    ore_accumulate_totali = ore_accumulate_presenze + ore_accumulate_straordinari
    ore_saldo = max(0.0, ore_accumulate_totali - ore_utilizzate)
    
    # 4. Calcola ore in scadenza nei prossimi 30 giorni
    ore_in_scadenza_30gg = 0.0
    data_scadenza_30gg = italian_now() + timedelta(days=30)
    # TODO: Implementare logica per calcolare ore che scadranno
    
    # 5. Calcola prossima scadenza
    prossima_scadenza = None
    if ore_in_scadenza_30gg > 0:
        prossima_scadenza = data_scadenza_30gg.date()
    
    # 6. Calcola percentuale utilizzo limite (server-side per sicurezza)
    percentuale_utilizzo = (ore_saldo / limite_max * 100) if limite_max > 0 else 0
    percentuale_utilizzo = min(100, max(0, percentuale_utilizzo))  # Clamp 0-100%
    
    # 7. Determina colore progress bar
    if percentuale_utilizzo < 50:
        color_class = 'bg-success'
    elif percentuale_utilizzo < 80:
        color_class = 'bg-warning'
    else:
        color_class = 'bg-danger'
    
    return {
        'ore_accumulate': round(ore_accumulate_totali, 2),
        'ore_utilizzate': round(ore_utilizzate, 2),
        'ore_saldo': round(ore_saldo, 2),
        'ore_in_scadenza_30gg': round(ore_in_scadenza_30gg, 2),
        'prossima_scadenza': prossima_scadenza,
        'limite_max': limite_max,
        'periodo_mesi': periodo_mesi,
        'percentuale_utilizzo': round(percentuale_utilizzo, 1),
        'color_class': color_class,
        'dettaglio': {
            'ore_da_presenze': round(ore_accumulate_presenze, 2),
            'ore_da_straordinari': round(ore_accumulate_straordinari, 2)
        }
    }

@banca_ore_bp.route('/my_banca_ore')
@login_required
def my_banca_ore():
    """Visualizza il dettaglio della banca ore personale"""
    if not current_user.can_view_my_banca_ore_widget():
        flash('Non hai i permessi per visualizzare questa sezione.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    if not current_user.banca_ore_enabled:
        flash('Non hai la banca ore abilitata.', 'info')
        return redirect(url_for('dashboard.dashboard'))
    
    # Calcola wallet completo
    wallet = calculate_banca_ore_balance(current_user.id)
    
    if not wallet:
        flash('Errore nel calcolo della banca ore.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    # TODO: Aggiungere cronologia movimenti
    cronologia_movimenti = []
    
    return render_template('banca_ore/my_banca_ore.html', 
                         wallet=wallet,
                         cronologia_movimenti=cronologia_movimenti)

@banca_ore_bp.route('/api/calculate_banca_ore_balance')
@login_required
def api_calculate_banca_ore_balance():
    """API per ottenere il saldo attuale della banca ore dell'utente"""
    if not current_user.banca_ore_enabled:
        return jsonify({'error': 'Banca ore non abilitata'}), 403
    
    wallet = calculate_banca_ore_balance(current_user.id)
    
    if not wallet:
        return jsonify({'error': 'Errore nel calcolo della banca ore'}), 500
    
    return jsonify(wallet)

@banca_ore_bp.route('/api/calculate_daily_overtime')
@login_required  
def api_calculate_daily_overtime():
    """API per calcolare straordinario giornaliero da presenza"""
    if not current_user.banca_ore_enabled:
        return jsonify({'error': 'Banca ore non abilitata'}), 403
    
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'error': 'Data richiesta'}), 400
    
    try:
        work_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Formato data non valido'}), 400
    
    overtime_hours = calculate_overtime_from_attendance(current_user.id, work_date)
    
    return jsonify({
        'date': date_str,
        'overtime_hours': overtime_hours,
        'overtime_formatted': format_hours(overtime_hours)
    })