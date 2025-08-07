#!/usr/bin/env python3
"""
Script per configurare i ruoli e permessi di base per Workly
"""

from app import app, db
from models import UserRole

def create_default_roles():
    """Crea i ruoli di base con i permessi appropriati"""
    
    # Definizione dei ruoli e permessi
    roles_data = {
        'Amministratore': {
            'description': 'Amministratore del sistema con accesso completo',
            'permissions': {
                # Dashboard e widget
                'can_access_dashboard': True,
                'can_view_team_stats_widget': True,
                'can_view_personal_leave_widget': True,
                'can_view_shifts_widget': True,
                'can_view_reperibilita_widget': True,
                'can_view_mileage_widget': True,
                # Gestione utenti
                'can_manage_users': True,
                'can_view_users': True,
                'can_edit_users': True,
                'can_delete_users': True,
                'can_create_users': True,
                # Gestione presenze
                'can_view_attendance': True,
                'can_manage_attendance': True,
                'can_view_all_attendance': True,
                'can_edit_attendance': True,
                # Gestione permessi
                'can_manage_leave_requests': True,
                'can_approve_leave_requests': True,
                'can_view_leave_requests': True,
                'can_create_leave_requests': True,
                # Gestione turni
                'can_manage_shifts': True,
                'can_view_shifts': True,
                'can_create_shifts': True,
                'can_edit_shifts': True,
                'can_delete_shifts': True,
                # Report
                'can_view_reports': True,
                'can_export_reports': True,
                # Sistema e configurazione
                'can_manage_system': True,
                'can_manage_roles': True,
                # can_view_roles non necessario - can_manage_roles include visualizzazione
                'can_manage_permissions': True,
                'can_manage_settings': True,
                'can_view_system_logs': True,
                # Gestione sedi
                'can_manage_sedi': True,
                'can_view_sedi': True,
                # Gestione reperibilità
                'can_manage_reperibilita': True,
                'can_view_reperibilita': True,
                # Gestione note spese
                'can_manage_expenses': True,
                'can_view_expenses': True,
                'can_approve_expenses': True,
                # Straordinari
                'can_manage_overtime': True,
                'can_view_overtime': True,
                'can_approve_overtime': True
            }
        },
        'Responsabile': {
            'description': 'Responsabile con permessi di supervisione',
            'permissions': {
                'can_access_dashboard': True,
                'can_view_users': True,
                'can_view_attendance': True,
                'can_view_all_attendance': True,
                'can_manage_attendance': True,
                'can_approve_leave_requests': True,
                'can_view_leave_requests': True,
                'can_manage_shifts': True,
                'can_view_shifts': True,
                'can_view_reports': True,
                'can_export_reports': True
            }
        },
        'Supervisore': {
            'description': 'Supervisore con permessi limitati',
            'permissions': {
                'can_access_dashboard': True,
                'can_view_attendance': True,
                'can_view_leave_requests': True,
                'can_view_shifts': True,
                'can_view_reports': True
            }
        },
        'Operatore': {
            'description': 'Operatore base',
            'permissions': {
                'can_access_dashboard': True,
                'can_view_attendance': True,
                'can_view_shifts': True
            }
        }
    }
    
    print("🔧 Configurazione ruoli e permessi...")
    
    for role_name, role_data in roles_data.items():
        # Cerca se il ruolo esiste già
        role = UserRole.query.filter_by(name=role_name).first()
        
        if role:
            print(f"📝 Aggiornamento ruolo esistente: {role_name}")
            role.description = role_data['description']
            role.permissions = role_data['permissions']
        else:
            print(f"➕ Creazione nuovo ruolo: {role_name}")
            role = UserRole(
                name=role_name,
                display_name=role_name,  # Aggiungo display_name obbligatorio
                description=role_data['description'],
                permissions=role_data['permissions'],
                active=True
            )
            db.session.add(role)
    
    try:
        db.session.commit()
        print("✅ Ruoli e permessi configurati con successo!")
        return True
    except Exception as e:
        print(f"❌ Errore durante la configurazione: {e}")
        db.session.rollback()
        return False

def main():
    with app.app_context():
        success = create_default_roles()
        
        if success:
            print("\n🎯 Verifica permessi utenti...")
            from models import User
            users = User.query.all()
            for user in users:
                print(f"{user.username}: can_access_dashboard = {user.can_access_dashboard()}")
        
        return success

if __name__ == '__main__':
    main()