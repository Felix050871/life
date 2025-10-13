"""
Multi-Tenant Utility Functions
Helper functions for managing multi-tenant data isolation
"""

from flask_login import current_user
from flask import abort
from functools import wraps

def get_user_company_id():
    """
    Ottiene il company_id dell'utente corrente
    System admin non hanno company_id (possono vedere tutto)
    """
    if not current_user.is_authenticated:
        return None
    
    # System admin possono vedere tutte le aziende
    if current_user.is_system_admin:
        return None
    
    return current_user.company_id

def filter_by_company(query, model_class):
    """
    Filtra una query per company_id dell'utente corrente
    Args:
        query: SQLAlchemy query object
        model_class: La classe del modello da filtrare
    Returns:
        Query filtrata per company
    """
    company_id = get_user_company_id()
    
    # System admin vedono tutto
    if company_id is None and current_user.is_authenticated and current_user.is_system_admin:
        return query
    
    # Filtra per company_id
    if hasattr(model_class, 'company_id'):
        return query.filter(model_class.company_id == company_id)
    
    return query

def require_same_company(resource_company_id):
    """
    Verifica che l'utente appartenga alla stessa azienda della risorsa
    System admin possono accedere a qualsiasi risorsa
    """
    if not current_user.is_authenticated:
        abort(401)
    
    # System admin possono accedere a tutto
    if current_user.is_system_admin:
        return True
    
    # Verifica che l'utente appartenga alla stessa azienda
    if current_user.company_id != resource_company_id:
        abort(403)
    
    return True

def get_company_users(company_id=None):
    """
    Ottiene tutti gli utenti di un'azienda
    Se company_id è None, usa quello dell'utente corrente
    """
    from models import User
    
    if company_id is None:
        company_id = get_user_company_id()
    
    # System admin possono specificare un'azienda
    if company_id is None and current_user.is_system_admin:
        return User.query.all()
    
    return User.query.filter_by(company_id=company_id).all()

def get_company_sedi(company_id=None):
    """
    Ottiene tutte le sedi di un'azienda
    Se company_id è None, usa quello dell'utente corrente
    """
    from models import Sede
    
    if company_id is None:
        company_id = get_user_company_id()
    
    # System admin possono specificare un'azienda
    if company_id is None and current_user.is_system_admin:
        return Sede.query.all()
    
    return Sede.query.filter_by(company_id=company_id).all()

def set_company_on_create(obj):
    """
    Imposta il company_id su un nuovo oggetto prima del commit
    Args:
        obj: Oggetto da salvare nel database
    """
    if hasattr(obj, 'company_id') and obj.company_id is None:
        obj.company_id = get_user_company_id()
    
    return obj

def require_company_access(f):
    """
    Decoratore per verificare l'accesso ai dati dell'azienda
    Blocca l'accesso cross-company per utenti non system admin
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        
        # System admin possono accedere a tutto
        if current_user.is_system_admin:
            return f(*args, **kwargs)
        
        # Utenti normali devono avere un company_id
        if not current_user.company_id:
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function
