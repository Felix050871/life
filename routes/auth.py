# =============================================================================
# AUTHENTICATION ROUTES BLUEPRINT
# Login, logout, password reset functionality
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from werkzeug.security import check_password_hash
from urllib.parse import urlparse, urljoin

from app import db
from models import User
from forms import LoginForm, ForgotPasswordForm, ResetPasswordForm

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
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.active and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            if next_page and is_safe_url(next_page):
                return redirect(next_page)
            return redirect(url_for('dashboard'))
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

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """Password reset request"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            # Create password reset token logic would go here
            flash('Se l\'email esiste nel sistema, riceverai le istruzioni per il reset', 'info')
        else:
            flash('Se l\'email esiste nel sistema, riceverai le istruzioni per il reset', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('forgot_password.html', form=form)

@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Password reset with token"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    # Token validation logic would go here
    form = ResetPasswordForm()
    if form.validate_on_submit():
        # Password reset logic would go here
        flash('Password resettata con successo', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('reset_password.html', form=form, token=token)