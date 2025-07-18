#!/usr/bin/env python3
"""
Script per aggiornare i nomi dei ruoli nel database
- Management -> Staff
- Responsabili -> Management
"""

from app import app, db
from models import User, UserRole

def update_role_names():
    with app.app_context():
        print("Aggiornamento nomi ruoli...")
        
        # Aggiorna gli utenti
        print("\n1. Aggiornamento utenti:")
        
        # Management -> Staff
        management_users = User.query.filter_by(role='Management').all()
        print(f"   - Trovati {len(management_users)} utenti con ruolo 'Management'")
        for user in management_users:
            user.role = 'Staff'
            print(f"     -> {user.username}: Management -> Staff")
        
        # Responsabili -> Management
        responsabili_users = User.query.filter_by(role='Responsabili').all()
        print(f"   - Trovati {len(responsabili_users)} utenti con ruolo 'Responsabili'")
        for user in responsabili_users:
            user.role = 'Management'
            print(f"     -> {user.username}: Responsabili -> Management")
        
        # Aggiorna i ruoli UserRole se esistono
        print("\n2. Aggiornamento tabella UserRole:")
        
        # Management -> Staff
        management_role = UserRole.query.filter_by(name='Management').first()
        if management_role:
            management_role.name = 'Staff'
            print("   - Management -> Staff")
        
        # Responsabili -> Management
        responsabili_role = UserRole.query.filter_by(name='Responsabili').first()
        if responsabili_role:
            responsabili_role.name = 'Management'
            print("   - Responsabili -> Management")
        
        # Salva le modifiche
        db.session.commit()
        print("\n✓ Aggiornamento completato!")
        
        # Verifica finale
        print("\n3. Verifica finale:")
        all_users = User.query.all()
        role_counts = {}
        for user in all_users:
            role_counts[user.role] = role_counts.get(user.role, 0) + 1
        
        for role, count in role_counts.items():
            print(f"   - {role}: {count} utenti")

if __name__ == '__main__':
    update_role_names()