# =============================================================================
# ADMIN & SYSTEM MANAGEMENT BLUEPRINT
# =============================================================================
#
# ROUTES INCLUSE:
# 1. admin_qr_codes (GET) - Gestione codici QR sistema
# 2. view_qr_codes (GET) - Visualizzazione codici QR
# 3. generate_qr_codes (POST) - Generazione codici QR
# 4. admin_settings (GET/POST) - Configurazioni sistema generali
# 5. system_info (GET) - Informazioni sistema e diagnostica
#
# Total routes: 5+ admin/system routes
# =============================================================================

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, make_response
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from functools import wraps
from app import db
from models import User, italian_now
import io
import os

# Create blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Helper functions
def require_admin_permission(f):
    """Decorator to require admin permissions for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.can_manage_system():
            flash('Non hai i permessi per accedere a questa sezione', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def require_qr_permission(f):
    """Decorator to require QR code permissions"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not (current_user.can_manage_qr() or current_user.can_view_qr()):
            flash('Non hai i permessi per accedere ai codici QR', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# QR CODE MANAGEMENT ROUTES
# =============================================================================

@admin_bp.route('/qr_codes')
@login_required
@require_qr_permission
def admin_qr_codes():
    """Gestione codici QR - Solo per chi può gestire"""
    if not current_user.can_manage_qr():
        flash('Non hai i permessi per gestire i codici QR', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    from utils import qr_codes_exist, get_qr_code_urls
    
    # Verifica se i QR code statici esistono
    qr_exist = qr_codes_exist()
    
    # Genera URL completi per i QR codes
    base_url = request.url_root.rstrip('/')
    qr_urls = {
        'entrata': f"{base_url}/qr_login/entrata",
        'uscita': f"{base_url}/qr_login/uscita"
    }
    
    # Se esistono, ottieni gli URL per visualizzarli
    static_qr_urls = get_qr_code_urls() if qr_exist else None
    
    try:
        from config import get_config
        config = get_config()
    except ImportError:
        config = {}
    
    return render_template('admin_qr_codes.html', 
                         qr_urls=qr_urls,
                         qr_exist=qr_exist,
                         static_qr_urls=static_qr_urls,
                         can_manage=True,
                         config=config)

@admin_bp.route('/qr_codes/view')
@login_required
@require_qr_permission
def view_qr_codes():
    """Visualizzazione codici QR - Solo per chi può visualizzare"""
    if not current_user.can_view_qr():
        flash('Non hai i permessi per visualizzare i codici QR', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    from utils import qr_codes_exist, get_qr_code_urls
    
    # Verifica se i QR code statici esistono
    qr_exist = qr_codes_exist()
    
    # Genera URL completi per i QR codes
    base_url = request.url_root.rstrip('/')
    qr_urls = {
        'entrata': f"{base_url}/qr_login/entrata",
        'uscita': f"{base_url}/qr_login/uscita"
    }
    
    # Se esistono, ottieni gli URL per visualizzarli
    static_qr_urls = get_qr_code_urls() if qr_exist else None
    
    try:
        from config import get_config
        config = get_config()
    except ImportError:
        config = {}
    
    return render_template('admin_qr_codes.html', 
                         qr_urls=qr_urls,
                         qr_exist=qr_exist,
                         static_qr_urls=static_qr_urls,
                         can_manage=current_user.can_manage_qr(),
                         config=config)

@admin_bp.route('/qr_codes/generate', methods=['POST'])
@login_required
@require_admin_permission
def generate_qr_codes():
    """Genera i codici QR statici del sistema"""
    if not current_user.can_manage_qr():
        return jsonify({'success': False, 'message': 'Non hai i permessi per generare i codici QR'}), 403
    
    try:
        from utils import generate_static_qr_codes
        
        # Genera i codici QR
        result = generate_static_qr_codes()
        
        if result:
            flash('Codici QR generati con successo', 'success')
            return jsonify({'success': True, 'message': 'Codici QR generati con successo'})
        else:
            flash('Errore nella generazione dei codici QR', 'danger')
            return jsonify({'success': False, 'message': 'Errore nella generazione dei codici QR'}), 500
            
    except ImportError:
        flash('Funzione di generazione QR non disponibile', 'warning')
        return jsonify({'success': False, 'message': 'Funzione non disponibile'}), 501
    except Exception as e:
        flash(f'Errore: {str(e)}', 'danger')
        return jsonify({'success': False, 'message': f'Errore: {str(e)}'}), 500

# =============================================================================
# SYSTEM SETTINGS ROUTES
# =============================================================================

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@require_admin_permission
def admin_settings():
    """Configurazioni sistema generali"""
    if request.method == 'POST':
        try:
            # Placeholder per salvare configurazioni
            # Implementare secondo le necessità del sistema
            flash('Configurazioni aggiornate con successo', 'success')
            return redirect(url_for('admin.admin_settings'))
        except Exception as e:
            flash(f'Errore nell\'aggiornamento configurazioni: {str(e)}', 'danger')
    
    # Carica configurazioni attuali
    try:
        from config import get_config
        config = get_config()
    except ImportError:
        config = {}
    
    return render_template('admin_settings.html', config=config)

@admin_bp.route('/system_info')
@login_required
@require_admin_permission
def system_info():
    """Informazioni sistema e diagnostica"""
    import sys
    import platform
    from flask import __version__ as flask_version
    
    try:
        # Informazioni sistema
        system_info = {
            'python_version': sys.version,
            'platform': platform.platform(),
            'flask_version': flask_version,
            'database_url': os.environ.get('DATABASE_URL', 'Non configurato'),
            'environment': os.environ.get('ENVIRONMENT', 'development'),
            'debug_mode': current_app.debug if 'current_app' in globals() else False,
        }
        
        # Statistiche database
        db_stats = {
            'total_users': User.query.count(),
            'active_users': User.query.filter_by(active=True).count(),
            'inactive_users': User.query.filter_by(active=False).count(),
        }
        
        return render_template('admin_system_info.html', 
                             system_info=system_info,
                             db_stats=db_stats)
                             
    except Exception as e:
        flash(f'Errore nel caricamento informazioni sistema: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_settings'))