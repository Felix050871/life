# =============================================================================
# INTERVENTIONS BLUEPRINT - Sistema gestione interventi generici
# =============================================================================
#
# ROUTES INCLUSE:
# 1. /start_general_intervention (POST) - Avvia nuovo intervento generico
# 2. /end_general_intervention (POST) - Termina intervento attivo
# 3. /my_interventions (GET) - Visualizza interventi personali/team
#
# Total routes: 3 intervention management routes
# =============================================================================

from flask import Blueprint, request, redirect, url_for, flash, render_template
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from models import AttendanceEvent, Intervention, ReperibilitaIntervention, User
from utils_tenant import filter_by_company, set_company_on_create

# Create blueprint
interventions_bp = Blueprint('interventions', __name__, url_prefix='/interventions')

# =============================================================================
# INTERVENTION MANAGEMENT ROUTES
# =============================================================================

@interventions_bp.route('/start', methods=['POST'])
@login_required
def start():
    """Inizia un nuovo intervento generico"""
    # Controlla se l'utente è presente
    user_status, _ = AttendanceEvent.get_user_status(current_user.id)
    if user_status != 'in':
        flash('Devi essere presente per iniziare un intervento.', 'warning')
        return redirect(url_for('dashboard.dashboard'))
    
    # Controlla se c'è già un intervento attivo (with company filter)
    active_intervention = filter_by_company(Intervention.query, Intervention).filter_by(
        user_id=current_user.id,
        end_datetime=None
    ).first()
    
    if active_intervention:
        flash('Hai già un intervento attivo. Terminalo prima di iniziarne un altro.', 'warning')
        return redirect(url_for('dashboard.dashboard'))
    
    # Ottieni i dati dal form
    description = request.form.get('description', '')
    priority = request.form.get('priority', 'Media')
    is_remote = request.form.get('is_remote', 'false').lower() == 'true'
    
    # Crea nuovo intervento
    from zoneinfo import ZoneInfo
    italy_tz = ZoneInfo('Europe/Rome')
    now = datetime.now(italy_tz)
    
    intervention = Intervention(
        user_id=current_user.id,
        start_datetime=now,
        description=description,
        priority=priority,
        is_remote=is_remote
    )
    set_company_on_create(intervention)
    
    try:
        db.session.add(intervention)
        db.session.commit()
        flash(f'Intervento in presenza iniziato alle {now.strftime("%H:%M")}', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Errore nel salvare l\'intervento', 'danger')
    
    return redirect(url_for('dashboard.dashboard'))

@interventions_bp.route('/end', methods=['POST'])
@login_required
def end():
    """Termina un intervento generico attivo"""
    # Trova l'intervento attivo (with company filter)
    active_intervention = filter_by_company(Intervention.query, Intervention).filter_by(
        user_id=current_user.id,
        end_datetime=None
    ).first()
    
    if not active_intervention:
        flash('Nessun intervento attivo trovato.', 'warning')
        return redirect(url_for('dashboard.dashboard'))
    
    # Termina l'intervento
    from zoneinfo import ZoneInfo
    italy_tz = ZoneInfo('Europe/Rome')
    now = datetime.now(italy_tz)
    
    active_intervention.end_datetime = now
    
    # Gestisci la descrizione finale
    end_description = request.form.get('end_description', '').strip()
    if end_description:
        # Combina descrizione iniziale e finale
        initial_desc = active_intervention.description or ''
        if initial_desc and end_description:
            active_intervention.description = f"{initial_desc}\n\n--- Risoluzione ---\n{end_description}"
        elif end_description:
            active_intervention.description = end_description
    
    try:
        db.session.commit()
        duration = active_intervention.duration_minutes
        flash(f'Intervento terminato alle {now.strftime("%H:%M")} (durata: {duration:.1f} minuti)', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Errore nel terminare l\'intervento', 'danger')
    
    return redirect(url_for('dashboard.dashboard'))

@interventions_bp.route('/my')
@login_required
def my():
    """Pagina per visualizzare gli interventi - tutti per PM/Ente, solo propri per altri utenti"""
    # Solo Admin non può accedere a questa pagina (non ha interventi)
    if current_user.role == 'Admin':
        flash('Accesso non autorizzato.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    from zoneinfo import ZoneInfo
    italy_tz = ZoneInfo('Europe/Rome')
    today = datetime.now(italy_tz).date()
    
    # Gestisci filtri data
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Default: primo del mese corrente - oggi
    if not start_date_str:
        start_date = today.replace(day=1)
    else:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    
    if not end_date_str:
        end_date = today
    else:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    # Converti le date in datetime per il filtro
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    # PM ed Ente vedono tutti gli interventi, altri utenti solo i propri
    if current_user.role in ['Management', 'Ente']:
        # Ottieni tutti gli interventi di reperibilità filtrati per data (with company filter)
        reperibilita_interventions = filter_by_company(ReperibilitaIntervention.query, ReperibilitaIntervention).join(User).filter(
            ReperibilitaIntervention.start_datetime >= start_datetime,
            ReperibilitaIntervention.start_datetime <= end_datetime
        ).order_by(ReperibilitaIntervention.start_datetime.desc()).all()
        
        # Ottieni tutti gli interventi generici filtrati per data (with company filter)
        general_interventions = filter_by_company(Intervention.query, Intervention).join(User).filter(
            Intervention.start_datetime >= start_datetime,
            Intervention.start_datetime <= end_datetime
        ).order_by(Intervention.start_datetime.desc()).all()
    else:
        # Ottieni solo gli interventi dell'utente corrente filtrati per data (with company filter)
        reperibilita_interventions = filter_by_company(ReperibilitaIntervention.query, ReperibilitaIntervention).filter(
            ReperibilitaIntervention.user_id == current_user.id,
            ReperibilitaIntervention.start_datetime >= start_datetime,
            ReperibilitaIntervention.start_datetime <= end_datetime
        ).order_by(ReperibilitaIntervention.start_datetime.desc()).all()
        
        general_interventions = filter_by_company(Intervention.query, Intervention).filter(
            Intervention.user_id == current_user.id,
            Intervention.start_datetime >= start_datetime,
            Intervention.start_datetime <= end_datetime
        ).order_by(Intervention.start_datetime.desc()).all()
    
    return render_template('my_interventions.html',
                         reperibilita_interventions=reperibilita_interventions,
                         general_interventions=general_interventions,
                         start_date=start_date,
                         end_date=end_date)