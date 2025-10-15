from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from models import CircleToolLink
from utils_tenant import filter_by_company, get_user_company_id, set_company_on_create
from sqlalchemy import asc

bp = Blueprint('circle_tools', __name__, url_prefix='/circle/tools')

@bp.route('/')
@login_required
def index():
    """Strumenti esterni - Scorciatoie"""
    if not current_user.has_permission('can_view_tools'):
        abort(403)
    
    tools = filter_by_company(
        CircleToolLink.query.filter_by(is_active=True),
        current_user
    ).order_by(asc(CircleToolLink.sort_order), asc(CircleToolLink.name)).all()
    
    # Raggruppa per categoria
    tools_by_category = {}
    for tool in tools:
        if tool.category not in tools_by_category:
            tools_by_category[tool.category] = []
        tools_by_category[tool.category].append(tool)
    
    return render_template('circle/tools/index.html', tools_by_category=tools_by_category)

@bp.route('/manage')
@login_required
def manage():
    """Gestione strumenti (solo admin)"""
    if not current_user.has_permission('can_manage_tools'):
        abort(403)
    
    tools = filter_by_company(
        CircleToolLink.query,
        current_user
    ).order_by(asc(CircleToolLink.sort_order)).all()
    
    return render_template('circle/tools/manage.html', tools=tools)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Crea nuovo strumento"""
    if not current_user.has_permission('can_manage_tools'):
        abort(403)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        url = request.form.get('url')
        icon = request.form.get('icon', 'fa-link')
        category = request.form.get('category', 'custom')
        sort_order = request.form.get('sort_order', 0)
        
        new_tool = CircleToolLink(
            name=name,
            description=description,
            url=url,
            icon=icon,
            category=category,
            sort_order=int(sort_order)
        )
        set_company_on_create(new_tool)
        
        db.session.add(new_tool)
        db.session.commit()
        
        flash('Strumento creato con successo!', 'success')
        return redirect(url_for('circle_tools.manage'))
    
    return render_template('circle/tools/create.html')

@bp.route('/<int:tool_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(tool_id):
    """Modifica strumento"""
    if not current_user.has_permission('can_manage_tools'):
        abort(403)
    
    tool = filter_by_company(CircleToolLink.query, current_user).get_or_404(tool_id)
    
    if request.method == 'POST':
        tool.name = request.form.get('name')
        tool.description = request.form.get('description')
        tool.url = request.form.get('url')
        tool.icon = request.form.get('icon')
        tool.category = request.form.get('category')
        tool.sort_order = int(request.form.get('sort_order', 0))
        tool.is_active = request.form.get('is_active') == 'on'
        
        db.session.commit()
        flash('Strumento aggiornato!', 'success')
        return redirect(url_for('circle_tools.manage'))
    
    return render_template('circle/tools/edit.html', tool=tool)

@bp.route('/<int:tool_id>/delete', methods=['POST'])
@login_required
def delete(tool_id):
    """Elimina strumento"""
    if not current_user.has_permission('can_manage_tools'):
        abort(403)
    
    tool = filter_by_company(CircleToolLink.query, current_user).get_or_404(tool_id)
    
    db.session.delete(tool)
    db.session.commit()
    
    flash('Strumento eliminato', 'success')
    return redirect(url_for('circle_tools.manage'))
