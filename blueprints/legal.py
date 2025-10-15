from flask import Blueprint, render_template

bp = Blueprint('legal', __name__, url_prefix='/legal')

@bp.route('/privacy')
def privacy():
    """Privacy Policy"""
    return render_template('legal/privacy.html')

@bp.route('/terms')
def terms():
    """Terms of Service"""
    return render_template('legal/terms.html')
