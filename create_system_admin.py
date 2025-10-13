#!/usr/bin/env python3
"""
Script per creare o promuovere un utente ad amministratore di sistema.
Gli amministratori di sistema possono gestire tutte le aziende del sistema multi-tenant.
"""

from app import app, db
from models import User
from werkzeug.security import generate_password_hash
import sys

def create_system_admin():
    """Crea o promuove un utente ad amministratore di sistema"""
    
    with app.app_context():
        print("=== CREAZIONE AMMINISTRATORE DI SISTEMA ===\n")
        
        # Mostra opzioni
        print("Scegli un'opzione:")
        print("1. Promuovi un utente esistente ad amministratore di sistema")
        print("2. Crea un nuovo amministratore di sistema")
        
        choice = input("\nOpzione (1 o 2): ").strip()
        
        if choice == '1':
            # Promuovi utente esistente
            users = User.query.filter_by(is_system_admin=False).all()
            
            if not users:
                print("\nNessun utente disponibile da promuovere.")
                return
            
            print("\nUtenti disponibili:")
            for idx, user in enumerate(users, 1):
                company_name = user.company.name if user.company else 'Nessuna'
                print(f"{idx}. {user.username} - {user.get_full_name()} (Azienda: {company_name})")
            
            user_idx = input("\nSeleziona utente (numero): ").strip()
            
            try:
                selected_user = users[int(user_idx) - 1]
                selected_user.is_system_admin = True
                selected_user.company_id = None  # System admin non appartiene a nessuna azienda
                
                db.session.commit()
                print(f"\n✓ {selected_user.username} è stato promosso ad amministratore di sistema")
                print(f"  L'utente è stato rimosso dall'azienda e può ora gestire tutte le aziende del sistema.")
            
            except (ValueError, IndexError):
                print("\nSelezione non valida.")
                return
        
        elif choice == '2':
            # Crea nuovo admin
            print("\n=== CREA NUOVO AMMINISTRATORE DI SISTEMA ===")
            
            username = input("Username: ").strip()
            if not username:
                print("Username obbligatorio")
                return
            
            # Verifica se l'username esiste già
            existing = User.query.filter_by(username=username).first()
            if existing:
                print(f"\nUsername '{username}' già esistente.")
                return
            
            email = input("Email: ").strip()
            if not email:
                print("Email obbligatoria")
                return
            
            # Verifica se l'email esiste già
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                print(f"\nEmail '{email}' già esistente.")
                return
            
            first_name = input("Nome: ").strip()
            last_name = input("Cognome: ").strip()
            password = input("Password (min 6 caratteri): ").strip()
            
            if len(password) < 6:
                print("Password troppo corta (minimo 6 caratteri)")
                return
            
            # Crea il nuovo admin
            new_admin = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password_hash=generate_password_hash(password),
                role='admin',  # Ruolo di base
                is_system_admin=True,  # Flag admin di sistema
                company_id=None,  # Non appartiene a nessuna azienda
                active=True
            )
            
            db.session.add(new_admin)
            db.session.commit()
            
            print(f"\n✓ Amministratore di sistema '{username}' creato con successo")
            print(f"  L'utente può ora accedere e gestire tutte le aziende del sistema.")
        
        else:
            print("\nOpzione non valida.")
            return
        
        # Mostra statistiche
        print("\n=== STATISTICHE AMMINISTRATORI DI SISTEMA ===")
        admins = User.query.filter_by(is_system_admin=True).all()
        print(f"Amministratori di sistema totali: {len(admins)}")
        for admin in admins:
            print(f"  - {admin.username} ({admin.get_full_name()})")

if __name__ == '__main__':
    create_system_admin()
