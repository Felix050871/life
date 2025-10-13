from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from models import (
    HublyPost, HublyGroup, HublyPoll, HublyCalendarEvent, 
    HublyDocument, HublyToolLink, User
)
from utils_tenant import filter_by_company, get_user_company_id
from datetime import datetime, timedelta
from sqlalchemy import desc

bp = Blueprint('hubly', __name__, url_prefix='/hubly')

@bp.route('/')
@login_required
def home():
    """Home page HUBLY con widget dinamici"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    company_id = get_user_company_id()
    
    # Widget: Ultimi post/news in evidenza (pinned)
    pinned_posts = filter_by_company(
        HublyPost.query.filter_by(published=True, pinned=True),
        current_user
    ).order_by(desc(HublyPost.created_at)).limit(3).all()
    
    # Widget: Ultime news/comunicazioni
    recent_posts = filter_by_company(
        HublyPost.query.filter_by(published=True, pinned=False),
        current_user
    ).order_by(desc(HublyPost.created_at)).limit(5).all()
    
    # Widget: Gruppi attivi
    active_groups = filter_by_company(
        HublyGroup.query.filter_by(is_private=False),
        current_user
    ).order_by(desc(HublyGroup.created_at)).limit(6).all()
    
    # Widget: Sondaggi attivi (non scaduti)
    now = datetime.utcnow()
    active_polls = filter_by_company(
        HublyPoll.query.filter(
            (HublyPoll.end_date == None) | (HublyPoll.end_date > now)
        ),
        current_user
    ).order_by(desc(HublyPoll.created_at)).limit(3).all()
    
    # Widget: Prossimi eventi calendario
    upcoming_events = filter_by_company(
        HublyCalendarEvent.query.filter(HublyCalendarEvent.start_datetime >= now),
        current_user
    ).order_by(HublyCalendarEvent.start_datetime).limit(5).all()
    
    # Widget: Strumenti rapidi
    quick_tools = filter_by_company(
        HublyToolLink.query.filter_by(is_active=True),
        current_user
    ).order_by(HublyToolLink.sort_order).limit(8).all()
    
    # Widget: Documenti recenti
    recent_documents = filter_by_company(
        HublyDocument.query.filter_by(is_active=True),
        current_user
    ).order_by(desc(HublyDocument.created_at)).limit(5).all()
    
    return render_template('hubly/home.html',
                         pinned_posts=pinned_posts,
                         recent_posts=recent_posts,
                         active_groups=active_groups,
                         active_polls=active_polls,
                         upcoming_events=upcoming_events,
                         quick_tools=quick_tools,
                         recent_documents=recent_documents)

@bp.route('/delorean')
@login_required
def delorean():
    """Sezione Delorean - Archivio storico aziendale"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    delorean_posts = filter_by_company(
        HublyPost.query.filter_by(post_type='delorean', published=True),
        current_user
    ).order_by(desc(HublyPost.created_at)).all()
    
    return render_template('hubly/delorean.html', posts=delorean_posts)

@bp.route('/personas')
@login_required
def personas():
    """Sezione Personas - Profili dipendenti"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    company_id = get_user_company_id()
    
    # Filtra utenti della stessa azienda, escludi system admin
    users = User.query.filter_by(
        company_id=company_id, 
        active=True,
        is_system_admin=False
    ).order_by(User.last_name, User.first_name).all()
    
    return render_template('hubly/personas.html', users=users)

@bp.route('/tech-feed')
@login_required
def tech_feed():
    """Feed tecnologico - Aggiornamenti IT/Tech"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    tech_posts = filter_by_company(
        HublyPost.query.filter_by(post_type='tech_feed', published=True),
        current_user
    ).order_by(desc(HublyPost.created_at)).all()
    
    return render_template('hubly/tech_feed.html', posts=tech_posts)
