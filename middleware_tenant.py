# =============================================================================
# TENANT CONTEXT MIDDLEWARE
# Path-based multi-tenancy: /t/<slug> routes for company-specific access
# =============================================================================

from flask import g, request, abort, redirect, url_for
from flask_login import current_user
from models import Company


def extract_tenant_slug_from_path():
    """
    Estrae lo slug del tenant dall'URL path.
    Pattern: /t/<slug>/...
    Restituisce None se non è un percorso tenant o se è un percorso admin.
    """
    path = request.path
    
    # Percorsi admin (SUPERADMIN) non hanno tenant
    if path.startswith('/admin/'):
        return None
    
    # Percorsi tenant: /t/<slug>/...
    if path.startswith('/t/'):
        parts = path[3:].split('/')  # Rimuove '/t/' e divide
        if parts and parts[0]:
            return parts[0]
    
    return None


def load_tenant_context():
    """
    Before request handler per caricare il contesto tenant.
    Legge lo slug dall'URL e carica l'azienda corrispondente in flask.g
    """
    g.tenant_company = None
    g.tenant_slug = None
    
    # Estrae slug dall'URL
    slug = extract_tenant_slug_from_path()
    
    if slug:
        # Cerca l'azienda dal database
        company = Company.query.filter_by(slug=slug, active=True).first()
        
        if not company:
            # Azienda non trovata o non attiva
            abort(404, description=f"Azienda non trovata: {slug}")
        
        # Salva in flask.g
        g.tenant_company = company
        g.tenant_slug = slug
        
        # Valida che l'utente loggato appartenga all'azienda corretta
        # (solo se l'utente è autenticato e NON è SUPERADMIN)
        if current_user.is_authenticated and not current_user.is_system_admin:
            if current_user.company_id != company.id:
                # L'utente sta cercando di accedere a un'azienda diversa dalla sua
                abort(403, description="Accesso negato: non appartieni a questa azienda")


def get_tenant_company():
    """
    Helper function per ottenere l'azienda tenant corrente.
    Restituisce None se non siamo in un contesto tenant.
    """
    return getattr(g, 'tenant_company', None)


def get_tenant_slug():
    """
    Helper function per ottenere lo slug tenant corrente.
    Restituisce None se non siamo in un contesto tenant.
    """
    return getattr(g, 'tenant_slug', None)


def require_tenant():
    """
    Decorator per routes che richiedono un contesto tenant.
    Redirige a /admin/login se non c'è tenant context.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not get_tenant_company():
                # Non siamo in un contesto tenant, redirige al login admin
                return redirect(url_for('auth.admin_login'))
            return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator
