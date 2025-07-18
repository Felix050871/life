#!/usr/bin/env python3
"""
Script per rimuovere completamente il ruolo Project Manager e sostituirlo con Management
"""

from app import app, db
from models import User, UserRole

def remove_project_manager():
    with app.app_context():
        print("Rimozione ruolo Project Manager...")
        
        # 1. Aggiorna tutti gli utenti Project Manager a Management
        pm_users = User.query.filter_by(role='Project Manager').all()
        print(f"\n1. Utenti Project Manager trovati: {len(pm_users)}")
        for user in pm_users:
            print(f"   - {user.username}: Project Manager -> Management")
            user.role = 'Management'
        
        # 2. Rimuovi il ruolo Project Manager dalla tabella UserRole
        pm_role = UserRole.query.filter_by(name='Project Manager').first()
        if pm_role:
            print(f"\n2. Rimozione ruolo UserRole 'Project Manager'")
            db.session.delete(pm_role)
        else:
            print(f"\n2. Ruolo 'Project Manager' non trovato in UserRole")
        
        # 3. Crea/Aggiorna il ruolo Management se non esiste
        management_role = UserRole.query.filter_by(name='Management').first()
        if not management_role:
            print(f"\n3. Creazione nuovo ruolo 'Management'")
            management_role = UserRole(
                name='Management',
                display_name='Management',
                description='Gestione locale sede con funzioni operative personali e supervisione sede',
                permissions={
                    'can_approve_leave': True,
                    'can_request_leave': True,
                    'can_access_attendance': True,
                    'can_access_dashboard': True
                },
                active=True
            )
            db.session.add(management_role)
        else:
            print(f"\n3. Ruolo 'Management' già esistente")
        
        # Salva tutte le modifiche
        db.session.commit()
        print("\n✓ Aggiornamento completato!")
        
        # Verifica finale
        print("\n4. Verifica finale:")
        all_users = User.query.all()
        role_counts = {}
        for user in all_users:
            role_counts[user.role] = role_counts.get(user.role, 0) + 1
        
        for role, count in sorted(role_counts.items()):
            print(f"   - {role}: {count} utenti")
        
        print("\nRuoli UserRole disponibili:")
        roles = UserRole.query.all()
        for role in roles:
            print(f"   - {role.name} ({role.display_name})")

if __name__ == '__main__':
    remove_project_manager()