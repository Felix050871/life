#!/usr/bin/env python3
"""
Script per reimpostare le password degli utenti
"""

from werkzeug.security import generate_password_hash
from app import app, db
from models import User

def reset_user_passwords():
    """Reimposta le password di tutti gli utenti"""
    
    # Definisci le password corrette
    user_passwords = {
        'admin': 'admin123',
        'responsabile': 'responsabile123',
        'dev': 'dev123',
        'operatore': 'operatore123',
        'redattore': 'redattore123',
        'management': 'management123'
    }
    
    with app.app_context():
        updated_count = 0
        
        for username, password in user_passwords.items():
            user = User.query.filter_by(username=username).first()
            if user:
                # Genera il nuovo hash della password
                new_password_hash = generate_password_hash(password)
                user.password_hash = new_password_hash
                updated_count += 1
                print(f"Password aggiornata per utente: {username}")
            else:
                print(f"Utente non trovato: {username}")
        
        if updated_count > 0:
            db.session.commit()
            print(f"\n✓ Aggiornate {updated_count} password nel database!")
        else:
            print("\nNessuna password aggiornata.")

if __name__ == "__main__":
    reset_user_passwords()