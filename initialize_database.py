#!/usr/bin/env python3
"""
Script Python per inizializzazione database Workly
con struttura corretta basata sui modelli attuali.
"""

import os
import sys
from datetime import datetime

def initialize_database():
    """Inizializza database con struttura corretta"""
    try:
        # Import corretto dal progetto attuale
        from main import app
        
        with app.app_context():
            # Import dei modelli dal file models.py corrente
            from models import db
            
            print("[INFO] Inizializzazione database...")
            
            # Crea tutte le tabelle basate sui modelli attuali
            db.create_all()
            
            # Verifica connessione
            result = db.session.execute(db.text('SELECT 1')).scalar()
            if result == 1:
                print("[OK] Database inizializzato e connessione verificata")
                return True
            else:
                print("[ERRORE] Problema connessione database")
                return False
                
    except Exception as e:
        print(f"[ERRORE] Inizializzazione database fallita: {e}")
        return False

def create_admin_user(username, email, password, first_name, last_name):
    """Crea utente amministratore con ruoli corretti"""
    try:
        from main import app
        
        with app.app_context():
            from models import db, User, UserRole
            from werkzeug.security import generate_password_hash
            
            # Controlla se utente esiste già
            existing_user = User.query.filter_by(username=username).first()
            existing_email = User.query.filter_by(email=email).first()
            
            if existing_user or existing_email:
                print("[ERRORE] Username o email già esistenti")
                return False
            
            # Crea o ottieni ruolo amministratore
            admin_role = UserRole.query.filter_by(name='Amministratore').first()
            if not admin_role:
                admin_role = UserRole(
                    name='Amministratore',
                    display_name='Amministratore',
                    description='Amministratore sistema con accesso completo',
                    permissions={
                        'can_manage_users': True,
                        'can_view_all_users': True,
                        'can_edit_all_users': True,
                        'can_delete_users': True,
                        'can_manage_roles': True,
                        'can_view_attendance': True,
                        'can_edit_attendance': True,
                        'can_manage_shifts': True,
                        'can_view_all_shifts': True,
                        'can_create_shifts': True,
                        'can_edit_shifts': True,
                        'can_delete_shifts': True,
                        'can_manage_holidays': True,
                        'can_view_reports': True,
                        'can_export_data': True,
                        'can_manage_sedi': True,
                        'can_view_dashboard': True,
                        'can_manage_leave_requests': True,
                        'can_approve_leave_requests': True,
                        'can_view_leave_requests': True,
                        'can_create_leave_requests': True,
                        'can_manage_overtime_requests': True,
                        'can_approve_overtime_requests': True,
                        'can_view_overtime_requests': True,
                        'can_create_overtime_requests': True,
                        'can_manage_mileage_requests': True,
                        'can_approve_mileage_requests': True,
                        'can_view_mileage_requests': True,
                        'can_create_mileage_requests': True,
                        'can_manage_internal_messages': True,
                        'can_send_internal_messages': True,
                        'can_view_internal_messages': True,
                        'can_manage_aci_tables': True,
                        'can_view_aci_tables': True
                    },
                    active=True
                )
                db.session.add(admin_role)
                db.session.flush()
            
            # Crea utente amministratore (CAMPO: active invece di is_active)
            admin_user = User(
                first_name=first_name,
                last_name=last_name,
                email=email,
                username=username,
                password_hash=generate_password_hash(password),
                active=True,  # CAMPO CORRETTO: active (non is_active)
                all_sedi=True,
                role='Amministratore'
            )
            
            db.session.add(admin_user)
            db.session.commit()
            
            print("[OK] Utente amministratore creato con successo")
            return True
            
    except Exception as e:
        print(f"[ERRORE] Creazione utente amministratore fallita: {e}")
        return False

if __name__ == "__main__":
    print("=== SCRIPT INIZIALIZZAZIONE DATABASE WORKLY ===")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Inizializza database
    if initialize_database():
        print("✓ Database inizializzato correttamente")
        
        # Chiedi se creare utente admin
        create_admin = input("Creare utente amministratore? (s/n): ").lower().strip()
        
        if create_admin in ['s', 'si', 'y', 'yes']:
            print("\nDati utente amministratore:")
            username = input("Username: ").strip()
            email = input("Email: ").strip()
            first_name = input("Nome: ").strip()
            last_name = input("Cognome: ").strip()
            password = input("Password: ").strip()
            
            if create_admin_user(username, email, password, first_name, last_name):
                print("✓ Utente amministratore creato")
            else:
                print("✗ Errore creazione utente amministratore")
    else:
        print("✗ Errore inizializzazione database")
        sys.exit(1)
    
    print("\n=== INIZIALIZZAZIONE COMPLETATA ===")
