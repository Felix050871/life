# =============================================================================
# AUTHENTICATION ROUTES BLUEPRINT
# Login, logout, password reset functionality
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from urllib.parse import urlparse, urljoin
from io import BytesIO
import secrets
import qrcode
import base64
from datetime import timedelta, datetime

from app import db
from models import User, PasswordResetToken
from forms import LoginForm, ForgotPasswordForm, ResetPasswordForm, ChangePasswordForm

# Create blueprint
auth_bp = Blueprint('auth', __name__)

def is_safe_url(target):
    """Check if a URL is safe for redirect (same domain only)"""
    if not target:
        return False
    
    # Parse the target URL
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    
    # Check if the scheme and netloc match (same domain)
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.active and user.password_hash and form.password.data and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            if next_page and is_safe_url(next_page):
                return redirect(next_page)
            return redirect(url_for('dashboard.dashboard'))
        flash('Username o password non validi', 'danger')
    
    return render_template('login.html', form=form)

@auth_bp.route('/logout')
def logout():
    """User logout"""
    logout_user()
    flash('Logout effettuato con successo', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/qr_login/<action>')
def qr_login(action):
    """QR code login for quick attendance marking"""
    if action not in ['clock_in', 'clock_out', 'break_start', 'break_end']:
        flash('Azione non valida', 'danger')
        return redirect(url_for('auth.login'))
    
    return render_template('qr_login.html', action=action)

# REMOVED DUPLICATE - Full implementation added below

# REMOVED DUPLICATE - Full implementation added below

@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Cambio password utente"""
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        # Verifica password attuale
        if not current_user.password_hash or not form.current_password.data or not check_password_hash(current_user.password_hash, form.current_password.data):
            flash('Password attuale non corretta', 'danger')
            return render_template('change_password.html', form=form)
        
        # Aggiorna password
        if form.new_password.data:
            current_user.password_hash = generate_password_hash(form.new_password.data)
        db.session.commit()
        
        flash('Password cambiata con successo', 'success')
        return redirect(url_for('dashboard.dashboard'))
    
    return render_template('change_password.html', form=form)

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """Richiesta reset password"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    
    form = ForgotPasswordForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            # Invalida token precedenti
            old_tokens = PasswordResetToken.query.filter_by(user_id=user.id, used=False).all()
            for token in old_tokens:
                token.used = True
            
            # Crea nuovo token - salva in UTC per evitare problemi timezone
            reset_token = PasswordResetToken()
            reset_token.user_id = user.id
            reset_token.token = secrets.token_urlsafe(32)
            reset_token.expires_at = datetime.utcnow() + timedelta(hours=1)  # Salva in UTC
            
            db.session.add(reset_token)
            db.session.commit()
            
            # Invia email con link reset password
            reset_url = url_for('auth.reset_password', token=reset_token.token, _external=True)
            try:
                from email_utils import send_password_reset_email
                send_password_reset_email(user, reset_url)
                flash('Se l\'email esiste nel sistema, riceverai un link per il reset della password', 'info')
            except Exception as e:
                # Fallback: mostra il link direttamente se l'email fallisce
                print(f"Errore invio email reset password: {str(e)}")
                flash(f'Link per il reset della password: {reset_url}', 'info')
        else:
            # Per sicurezza, non rivelare se l'email esiste o meno
            flash('Se l\'email esiste nel sistema, riceverai un link per il reset della password', 'info')
        
        return redirect(url_for('auth.login'))
    
    return render_template('forgot_password.html', form=form)

@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password con token"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    
    # Trova il token
    reset_token = PasswordResetToken.query.filter_by(token=token).first()
    
    # Controlla se il token esiste, non è scaduto e non è già stato usato
    if not reset_token or reset_token.is_expired or reset_token.used:
        flash('Token non valido o scaduto', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        # Aggiorna password
        if form.new_password.data:
            reset_token.user.password_hash = generate_password_hash(form.new_password.data)
        
        # Marca token come usato
        reset_token.used = True
        
        db.session.commit()
        
        flash('Password reimpostata con successo. Puoi ora accedere con la nuova password', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('reset_password.html', form=form, token=token)

# =============================================================================
# QR CODE ROUTES
# =============================================================================

@auth_bp.route('/qr_fresh/<action>')
def qr_fresh(action):
    """Route per QR dal browser - forza logout e redirect a qr_login"""
    if action not in ['entrata', 'uscita']:
        flash('Azione non valida', 'error')
        return redirect(url_for('auth.login'))
    
    # Forza logout se utente autenticato (dal browser)
    if current_user.is_authenticated:
        logout_user()
        flash('Disconnesso per accesso QR', 'info')
    
    # Redirect alla pagina QR login
    return redirect(url_for('auth.qr_login', action=action))

@auth_bp.route('/generate_qr_codes')
def generate_qr_codes():
    """Genera i codici QR per entrata e uscita"""
    try:
        base_url = request.url_root.rstrip('/')
        
        # URLs per entrata e uscita
        entry_url = f"{base_url}/auth/qr_login/entrata"
        exit_url = f"{base_url}/auth/qr_login/uscita"
        
        # Genera QR Code per entrata (semplificato)
        qr_entry = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr_entry.add_data(entry_url)
        qr_entry.make(fit=True)
        
        # Crea immagine con colori default
        entry_img = qr_entry.make_image(fill_color="black", back_color="white")
        entry_buffer = BytesIO()
        entry_img.save(entry_buffer, format='PNG')
        entry_buffer.seek(0)
        entry_qr_data = base64.b64encode(entry_buffer.getvalue()).decode()
        
        # Genera QR Code per uscita (semplificato)
        qr_exit = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr_exit.add_data(exit_url)
        qr_exit.make(fit=True)
        
        # Crea immagine con colori default
        exit_img = qr_exit.make_image(fill_color="black", back_color="white")
        exit_buffer = BytesIO()
        exit_img.save(exit_buffer, format='PNG')
        exit_buffer.seek(0)
        exit_qr_data = base64.b64encode(exit_buffer.getvalue()).decode()
        
        return render_template('qr_codes.html',
                             entry_qr=entry_qr_data,
                             exit_qr=exit_qr_data,
                             entry_url=entry_url,
                             exit_url=exit_url)
                             
    except Exception as e:
        flash(f'Errore nella generazione dei codici QR: {str(e)}', 'error')
        return redirect(url_for('dashboard.dashboard'))

@auth_bp.route('/qr/<action>')
def qr_page(action):
    """Pagine dedicate per QR Code di entrata e uscita"""
    if action not in ['entrata', 'uscita']:
        return redirect(url_for('auth.login'))
    
    # Genera URL completo per il QR code
    base_url = request.url_root.rstrip('/')
    qr_url = f"{base_url}/auth/qr_login/{action}"
    
    return render_template('qr_page.html', action=action, qr_url=qr_url)