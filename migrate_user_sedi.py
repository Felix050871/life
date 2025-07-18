#!/usr/bin/env python3
"""
Script di migrazione per creare la tabella user_sede_association
e migrare i dati esistenti dalle associazioni sede_id legacy
"""

import os
import sys
from sqlalchemy import text

# Aggiungi il path del progetto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Sede

def migrate_user_sedi():
    with app.app_context():
        try:
            # Crea la tabella di associazione se non esiste
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS user_sede_association (
                    user_id INTEGER NOT NULL,
                    sede_id INTEGER NOT NULL,
                    PRIMARY KEY (user_id, sede_id),
                    FOREIGN KEY(user_id) REFERENCES "user" (id),
                    FOREIGN KEY(sede_id) REFERENCES sede (id)
                )
            """))
            
            print("✓ Tabella user_sede_association creata/verificata")
            
            # Migra i dati esistenti da sede_id a associazioni multiple
            users_with_sede = User.query.filter(User.sede_id.isnot(None)).all()
            migrated_count = 0
            
            for user in users_with_sede:
                # Verifica se l'associazione esiste già
                existing = db.session.execute(text("""
                    SELECT 1 FROM user_sede_association 
                    WHERE user_id = :user_id AND sede_id = :sede_id
                """), {"user_id": user.id, "sede_id": user.sede_id}).first()
                
                if not existing:
                    # Inserisci l'associazione
                    db.session.execute(text("""
                        INSERT INTO user_sede_association (user_id, sede_id) 
                        VALUES (:user_id, :sede_id)
                    """), {"user_id": user.id, "sede_id": user.sede_id})
                    migrated_count += 1
                    print(f"  - Migrato utente {user.username} -> sede {user.sede_id}")
            
            # Associa automaticamente tutte le sedi agli utenti Management
            management_users = User.query.filter_by(role='Management').all()
            all_sedi = Sede.query.filter_by(active=True).all()
            
            for user in management_users:
                for sede in all_sedi:
                    # Verifica se l'associazione esiste già
                    existing = db.session.execute(text("""
                        SELECT 1 FROM user_sede_association 
                        WHERE user_id = :user_id AND sede_id = :sede_id
                    """), {"user_id": user.id, "sede_id": sede.id}).first()
                    
                    if not existing:
                        # Inserisci l'associazione
                        db.session.execute(text("""
                            INSERT INTO user_sede_association (user_id, sede_id) 
                            VALUES (:user_id, :sede_id)
                        """), {"user_id": user.id, "sede_id": sede.id})
                        print(f"  - Associato utente Management {user.username} -> sede {sede.name}")
            
            db.session.commit()
            print(f"✓ Migrazione completata. {migrated_count} associazioni migrate")
            print(f"✓ Utenti Management associati automaticamente a tutte le sedi")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Errore durante la migrazione: {e}")
            raise

if __name__ == "__main__":
    migrate_user_sedi()