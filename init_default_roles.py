#!/usr/bin/env python3
"""
Script per inizializzare i ruoli di default nel sistema Workly
"""

from app import app, db
from models import UserRole

def init_default_roles():
    """Inizializza i ruoli di default se non esistono"""
    with app.app_context():
        # Definisci i ruoli di default con i loro permessi
        default_roles = [
            {
                'name': 'Admin',
                'display_name': 'Amministratore',
                'description': 'Accesso completo a tutte le funzionalità del sistema',
                'permissions': {
                    'can_manage_users': True,
                    'can_manage_shifts': True,
                    'can_approve_leave': True,
                    'can_request_leave': False,
                    'can_access_attendance': True,
                    'can_access_dashboard': True,
                    'can_view_reports': True,
                    'can_manage_sedi': True,
                    'can_manage_roles': True
                }
            },
            {
                'name': 'Project Manager',
                'display_name': 'Project Manager',
                'description': 'Gestione progetti e approvazione richieste',
                'permissions': {
                    'can_manage_users': False,
                    'can_manage_shifts': True,
                    'can_approve_leave': True,
                    'can_request_leave': True,
                    'can_access_attendance': True,
                    'can_access_dashboard': True,
                    'can_view_reports': True,
                    'can_manage_sedi': False,
                    'can_manage_roles': False
                }
            },
            {
                'name': 'Redattore',
                'display_name': 'Redattore',
                'description': 'Redattore con accesso base',
                'permissions': {
                    'can_manage_users': False,
                    'can_manage_shifts': False,
                    'can_approve_leave': False,
                    'can_request_leave': True,
                    'can_access_attendance': True,
                    'can_access_dashboard': True,
                    'can_view_reports': False,
                    'can_manage_sedi': False,
                    'can_manage_roles': False
                }
            },
            {
                'name': 'Sviluppatore',
                'display_name': 'Sviluppatore',
                'description': 'Sviluppatore con accesso tecnico',
                'permissions': {
                    'can_manage_users': False,
                    'can_manage_shifts': False,
                    'can_approve_leave': False,
                    'can_request_leave': True,
                    'can_access_attendance': True,
                    'can_access_dashboard': True,
                    'can_view_reports': False,
                    'can_manage_sedi': False,
                    'can_manage_roles': False
                }
            },
            {
                'name': 'Operatore',
                'display_name': 'Operatore',
                'description': 'Operatore con accesso operativo',
                'permissions': {
                    'can_manage_users': False,
                    'can_manage_shifts': False,
                    'can_approve_leave': False,
                    'can_request_leave': True,
                    'can_access_attendance': True,
                    'can_access_dashboard': True,
                    'can_view_reports': False,
                    'can_manage_sedi': False,
                    'can_manage_roles': False
                }
            },
            {
                'name': 'Management',
                'display_name': 'Management',
                'description': 'Ruolo di management con accesso ai report ma non alle operazioni quotidiane',
                'permissions': {
                    'can_manage_users': False,
                    'can_manage_shifts': False,
                    'can_approve_leave': False,
                    'can_request_leave': False,
                    'can_access_attendance': False,
                    'can_access_dashboard': False,
                    'can_view_reports': True,
                    'can_manage_sedi': False,
                    'can_manage_roles': False
                }
            }
        ]
        
        # Crea i ruoli se non esistono
        for role_data in default_roles:
            existing_role = UserRole.query.filter_by(name=role_data['name']).first()
            if not existing_role:
                new_role = UserRole(
                    name=role_data['name'],
                    display_name=role_data['display_name'],
                    description=role_data['description'],
                    permissions=role_data['permissions'],
                    active=True
                )
                db.session.add(new_role)
                print(f"Creato ruolo: {role_data['display_name']}")
            else:
                print(f"Ruolo già esistente: {role_data['display_name']}")
        
        db.session.commit()
        print("Inizializzazione ruoli completata!")

if __name__ == '__main__':
    init_default_roles()