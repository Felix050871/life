# =============================================================================
# QR CODE BLUEPRINT - Sistema QR code per presenze rapide
# =============================================================================
#
# ROUTES INCLUSE:
# 1. /qr_login/<action> (GET/POST) - Pagina login con QR code per entrata/uscita
# 2. /qr_fresh/<action> (GET) - Route QR dal browser con logout forzato
# 3. /quick_attendance/<action> (GET/POST) - Registrazione rapida presenze via QR
# 4. /generate_qr_codes (GET) - Genera codici QR per entrata e uscita
# 5. /qr/<action> (GET) - Gestione QR generici con template
#
# Total routes: 5 QR code management routes
# =============================================================================

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, make_response, session
from flask_login import login_required, current_user, login_user, logout_user
from datetime import datetime, date, timedelta, time
from functools import wraps
from app import db
from models import User, AttendanceEvent, Sede, italian_now
from forms import LoginForm
import qrcode
import base64
from io import BytesIO
from werkzeug.security import check_password_hash
from utils_tenant import filter_by_company, set_company_on_create

# Create blueprint
qr_bp = Blueprint('qr', __name__, url_prefix='/qr')

# Helper functions
def require_login(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# QR CODE LOGIN ROUTES
# =============================================================================

@qr_bp.route('/login/<action>', methods=['GET', 'POST'])
def login(action):
    """Pagina di login con QR code per entrata/uscita rapida"""
    if action not in ['entrata', 'uscita']:
        flash('Azione non valida', 'error')
        return redirect(url_for('auth.login'))
    
    # Forza logout per permettere nuovo login da QR
    if current_user.is_authenticated:
        logout_user()
        session.clear()
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = filter_by_company(User.query).filter_by(username=form.username.data).first()
        if user and user.active and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            return redirect(url_for('qr.quick_attendance', action=action))
        else:
            flash('Username o password non validi', 'error')
    
    return render_template('qr_login_standalone.html', form=form, action=action)

@qr_bp.route('/fresh/<action>')
def fresh(action):
    """Route per QR dal browser - forza logout e redirect a qr_login"""
    if action not in ['entrata', 'uscita']:
        flash('Azione non valida', 'error')
        return redirect(url_for('auth.login'))
    
    # Forza logout se già loggato per permettere nuovo login
    if current_user.is_authenticated:
        logout_user()
        session.clear()
    
    # Redirect al login QR
    return redirect(url_for('qr.login', action=action))

# =============================================================================
# QUICK ATTENDANCE ROUTES
# =============================================================================

@qr_bp.route('/attendance/<action>', methods=['GET', 'POST'])
@require_login
def quick_attendance(action):
    """Gestisce la registrazione rapida di entrata/uscita tramite QR"""
    if action not in ['entrata', 'uscita']:
        flash('Azione non valida', 'error')
        return redirect(url_for('dashboard.dashboard'))
    
    from zoneinfo import ZoneInfo
    italy_tz = ZoneInfo('Europe/Rome')
    now = datetime.now(italy_tz)
    
    # Verifica stato attuale dell'utente
    user_status, last_event = AttendanceEvent.get_user_status(current_user.id)
    
    if request.method == 'POST':
        # Determina sede_id
        sede_id = None
        if current_user.all_sedi:
            # Utente multi-sede: prendi sede dal form se presente
            sede_id = request.form.get('sede_id')
            if sede_id:
                sede_id = int(sede_id)
        elif current_user.sede_id:
            # Utente mono-sede: usa la sua sede
            sede_id = current_user.sede_id
        
        # Processa l'azione
        success = False
        message = ""
        
        if action == 'entrata':
            if user_status == 'out':
                # Clock in
                event = AttendanceEvent(
                    user_id=current_user.id,
                    date=now.date(),
                    event_type='clock_in',
                    timestamp=now,
                    sede_id=sede_id,
                    notes=request.form.get('notes', '')
                )
                set_company_on_create(event)
                db.session.add(event)
                db.session.commit()
                
                success = True
                message = f"Entrata registrata alle {now.strftime('%H:%M')}"
            else:
                message = "Sei già dentro! Non puoi registrare un'altra entrata."
                
        elif action == 'uscita':
            if user_status == 'in':
                # Clock out
                event = AttendanceEvent(
                    user_id=current_user.id,
                    date=now.date(),
                    event_type='clock_out',
                    timestamp=now,
                    sede_id=sede_id,
                    notes=request.form.get('notes', '')
                )
                set_company_on_create(event)
                db.session.add(event)
                db.session.commit()
                
                success = True
                message = f"Uscita registrata alle {now.strftime('%H:%M')}"
            else:
                message = "Non sei dentro! Non puoi registrare un'uscita."
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'warning')
        
        # Redirect per evitare re-submit
        return redirect(url_for('qr.quick_attendance', action=action))
    
    # GET request: mostra il form
    available_sedi = []
    if current_user.all_sedi:
        available_sedi = filter_by_company(Sede.query).filter_by(active=True).all()
    
    # Ottieni eventi di oggi per le statistiche
    today_events = AttendanceEvent.get_daily_events(current_user.id)
    today_hours = AttendanceEvent.get_daily_work_hours(current_user.id)
    
    return render_template('quick_attendance.html',
                         action=action,
                         user_status=user_status,
                         last_event=last_event,
                         today_events=today_events,
                         today_hours=today_hours,
                         available_sedi=available_sedi,
                         current_time=now)

# =============================================================================
# QR CODE GENERATION ROUTES
# =============================================================================

@qr_bp.route('/generate')
def generate_codes():
    """Genera i codici QR per entrata e uscita"""
    try:
        # Genera QR codes per entrata e uscita
        base_url = request.url_root.rstrip('/')
        
        entry_url = f"{base_url}/qr/login/entrata"
        exit_url = f"{base_url}/qr/login/uscita"
        
        # Genera QR Code per entrata (semplificato)
        qr_entry = qrcode.QRCode(version=1, box_size=10, border=5)
        qr_entry.add_data(entry_url)
        qr_entry.make(fit=True)
        
        img_entry = qr_entry.make_image(fill_color="black", back_color="white")
        
        # Genera QR Code per uscita
        qr_exit = qrcode.QRCode(version=1, box_size=10, border=5)
        qr_exit.add_data(exit_url)
        qr_exit.make(fit=True)
        
        img_exit = qr_exit.make_image(fill_color="black", back_color="white")
        
        # Converti in base64 per HTML
        buffer_entry = BytesIO()
        img_entry.save(buffer_entry, format='PNG')
        img_entry_base64 = base64.b64encode(buffer_entry.getvalue()).decode()
        
        buffer_exit = BytesIO()
        img_exit.save(buffer_exit, format='PNG')
        img_exit_base64 = base64.b64encode(buffer_exit.getvalue()).decode()
        
        return render_template('generated_qr_codes.html',
                             entry_qr=img_entry_base64,
                             exit_qr=img_exit_base64,
                             entry_url=entry_url,
                             exit_url=exit_url)
                             
    except Exception as e:
        flash(f'Errore nella generazione dei QR Code: {str(e)}', 'error')
        return redirect(url_for('dashboard.dashboard'))

@qr_bp.route('/page/<action>')
def page(action):
    """Gestione QR generici con template"""
    if action not in ['entrata', 'uscita']:
        flash('Azione non valida', 'error')
        return redirect(url_for('dashboard.dashboard'))
    
    # Genera URL per il QR code
    base_url = request.url_root.rstrip('/')
    qr_url = f"{base_url}/qr/login/{action}"
    
    return render_template('qr_page.html', action=action, qr_url=qr_url)

# =============================================================================
# QR CODE API ROUTES
# =============================================================================

@qr_bp.route('/api/status')
@login_required
def api_status():
    """API per ottenere lo stato attuale dell'utente"""
    try:
        user_status, last_event = AttendanceEvent.get_user_status(current_user.id)
        today_hours = AttendanceEvent.get_daily_work_hours(current_user.id)
        
        from zoneinfo import ZoneInfo
        italy_tz = ZoneInfo('Europe/Rome')
        now = datetime.now(italy_tz)
        
        return jsonify({
            'success': True,
            'user': {
                'name': current_user.get_full_name(),
                'role': current_user.role
            },
            'status': user_status,
            'current_time': now.strftime('%H:%M'),
            'today_hours': f"{today_hours:.2f}",
            'last_event': {
                'type': last_event.event_type if last_event else None,
                'time': last_event.timestamp.strftime('%H:%M') if last_event else None
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@qr_bp.route('/api/quick_action', methods=['POST'])
@login_required
def api_quick_action():
    """API per azioni rapide di presenza via AJAX"""
    try:
        action = request.json.get('action')
        notes = request.json.get('notes', '')
        sede_id = request.json.get('sede_id')
        
        if action not in ['entrata', 'uscita']:
            return jsonify({
                'success': False,
                'error': 'Azione non valida'
            }), 400
        
        from zoneinfo import ZoneInfo
        italy_tz = ZoneInfo('Europe/Rome')
        now = datetime.now(italy_tz)
        
        # Verifica stato attuale
        user_status, _ = AttendanceEvent.get_user_status(current_user.id)
        
        # Determina sede_id
        if not sede_id and current_user.sede_id:
            sede_id = current_user.sede_id
        elif sede_id:
            sede_id = int(sede_id)
        
        # Processa l'azione
        if action == 'entrata' and user_status == 'out':
            event = AttendanceEvent(
                user_id=current_user.id,
                date=now.date(),
                event_type='clock_in',
                timestamp=now,
                sede_id=sede_id,
                notes=notes
            )
            set_company_on_create(event)
            db.session.add(event)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f"Entrata registrata alle {now.strftime('%H:%M')}",
                'new_status': 'in'
            })
            
        elif action == 'uscita' and user_status == 'in':
            event = AttendanceEvent(
                user_id=current_user.id,
                date=now.date(),
                event_type='clock_out',
                timestamp=now,
                sede_id=sede_id,
                notes=notes
            )
            set_company_on_create(event)
            db.session.add(event)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f"Uscita registrata alle {now.strftime('%H:%M')}",
                'new_status': 'out'
            })
        else:
            message = "Sei già dentro!" if user_status == 'in' and action == 'entrata' else "Non sei dentro!"
            return jsonify({
                'success': False,
                'error': message
            }), 400
            
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Errore durante l\'operazione: {str(e)}'
        }), 500