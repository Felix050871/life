from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from models import HublyPoll, HublyPollOption, HublyPollVote
from utils_tenant import filter_by_company, get_user_company_id, set_company_on_create
from sqlalchemy import desc
from datetime import datetime

bp = Blueprint('hubly_polls', __name__, url_prefix='/hubly/polls')

@bp.route('/')
@login_required
def index():
    """Lista di tutti i sondaggi"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    # Sondaggi attivi (non chiusi)
    active_polls = filter_by_company(
        HublyPoll.query,
        current_user
    ).order_by(desc(HublyPoll.created_at)).all()
    
    # Filtra per stato
    open_polls = [p for p in active_polls if not p.is_closed()]
    closed_polls = [p for p in active_polls if p.is_closed()]
    
    return render_template('hubly/polls/index.html', 
                         open_polls=open_polls,
                         closed_polls=closed_polls)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Crea nuovo sondaggio"""
    if not current_user.has_permission('can_create_polls'):
        abort(403)
    
    if request.method == 'POST':
        question = request.form.get('question')
        description = request.form.get('description')
        is_anonymous = request.form.get('is_anonymous') == 'on'
        multiple_choice = request.form.get('multiple_choice') == 'on'
        end_date_str = request.form.get('end_date')
        
        if not question:
            flash('La domanda è obbligatoria', 'danger')
            return redirect(url_for('hubly_polls.create'))
        
        # Opzioni (almeno 2)
        options = request.form.getlist('options[]')
        options = [opt.strip() for opt in options if opt.strip()]
        
        if len(options) < 2:
            flash('Devi fornire almeno 2 opzioni', 'danger')
            return redirect(url_for('hubly_polls.create'))
        
        # Parse end_date
        end_date = None
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Formato data non valido', 'danger')
                return redirect(url_for('hubly_polls.create'))
        
        # Crea sondaggio
        poll = HublyPoll(
            question=question,
            description=description,
            creator_id=current_user.id,
            is_anonymous=is_anonymous,
            multiple_choice=multiple_choice,
            end_date=end_date,
            company_id=get_user_company_id(current_user)
        )
        
        db.session.add(poll)
        db.session.flush()  # Per ottenere poll.id
        
        # Crea opzioni
        for option_text in options:
            option = HublyPollOption(
                poll_id=poll.id,
                option_text=option_text
            )
            db.session.add(option)
        
        db.session.commit()
        
        flash('Sondaggio creato con successo!', 'success')
        return redirect(url_for('hubly_polls.view', poll_id=poll.id))
    
    return render_template('hubly/polls/create.html')

@bp.route('/<int:poll_id>')
@login_required
def view(poll_id):
    """Visualizza sondaggio e risultati"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    poll = filter_by_company(HublyPoll.query, current_user).filter_by(id=poll_id).first_or_404()
    
    # Ottieni risultati
    results = poll.get_results()
    
    # Verifica se l'utente ha votato
    has_voted = poll.has_voted(current_user)
    user_votes = poll.get_user_votes(current_user) if has_voted else []
    
    return render_template('hubly/polls/view.html', 
                         poll=poll, 
                         results=results,
                         has_voted=has_voted,
                         user_votes=user_votes)

@bp.route('/<int:poll_id>/vote', methods=['POST'])
@login_required
def vote(poll_id):
    """Vota in un sondaggio"""
    if not current_user.has_permission('can_vote_polls'):
        abort(403)
    
    poll = filter_by_company(HublyPoll.query, current_user).filter_by(id=poll_id).first_or_404()
    
    # Verifica se il sondaggio è chiuso
    if poll.is_closed():
        flash('Questo sondaggio è chiuso', 'warning')
        return redirect(url_for('hubly_polls.view', poll_id=poll_id))
    
    # Verifica se ha già votato
    if poll.has_voted(current_user) and not poll.multiple_choice:
        flash('Hai già votato in questo sondaggio', 'warning')
        return redirect(url_for('hubly_polls.view', poll_id=poll_id))
    
    # Ottieni opzioni selezionate
    if poll.multiple_choice:
        option_ids = request.form.getlist('option_ids[]')
    else:
        option_id = request.form.get('option_id')
        option_ids = [option_id] if option_id else []
    
    if not option_ids:
        flash('Devi selezionare almeno un\'opzione', 'danger')
        return redirect(url_for('hubly_polls.view', poll_id=poll_id))
    
    # Rimuovi voti precedenti se esiste
    HublyPollVote.query.filter_by(poll_id=poll_id, user_id=current_user.id).delete()
    
    # Aggiungi nuovi voti
    for option_id in option_ids:
        option = HublyPollOption.query.filter_by(id=option_id, poll_id=poll_id).first()
        if option:
            vote = HublyPollVote(
                poll_id=poll_id,
                option_id=int(option_id),
                user_id=current_user.id
            )
            db.session.add(vote)
    
    db.session.commit()
    
    flash('Voto registrato!', 'success')
    return redirect(url_for('hubly_polls.view', poll_id=poll_id))

@bp.route('/<int:poll_id>/delete', methods=['POST'])
@login_required
def delete(poll_id):
    """Elimina sondaggio"""
    poll = filter_by_company(HublyPoll.query, current_user).filter_by(id=poll_id).first_or_404()
    
    # Solo creatore o utenti con can_manage_polls possono eliminare
    if poll.creator_id != current_user.id and not current_user.has_permission('can_manage_polls'):
        abort(403)
    
    # Elimina voti
    HublyPollVote.query.filter_by(poll_id=poll_id).delete()
    
    # Elimina opzioni
    HublyPollOption.query.filter_by(poll_id=poll_id).delete()
    
    # Elimina sondaggio
    db.session.delete(poll)
    db.session.commit()
    
    flash('Sondaggio eliminato', 'success')
    return redirect(url_for('hubly_polls.index'))

@bp.route('/<int:poll_id>/close', methods=['POST'])
@login_required
def close(poll_id):
    """Chiudi sondaggio anticipatamente"""
    poll = filter_by_company(HublyPoll.query, current_user).filter_by(id=poll_id).first_or_404()
    
    # Solo creatore o utenti con can_manage_polls possono chiudere
    if poll.creator_id != current_user.id and not current_user.has_permission('can_manage_polls'):
        abort(403)
    
    # Imposta end_date a ora
    from utils import italian_now
    poll.end_date = italian_now()
    db.session.commit()
    
    flash('Sondaggio chiuso', 'success')
    return redirect(url_for('hubly_polls.view', poll_id=poll_id))
