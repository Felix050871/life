#!/usr/bin/env python3
"""
Script per aggiungere il campo all_sedi alla tabella user
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User

def add_all_sedi_field():
    """Aggiunge il campo all_sedi alla tabella user"""
    with app.app_context():
        try:
            # Verifica se il campo esiste già
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = [column['name'] for column in inspector.get_columns('user')]
            
            if 'all_sedi' in columns:
                print("✓ Campo all_sedi già presente nella tabella user")
                return True
            
            # Aggiungi il campo all_sedi
            print("📝 Aggiunta del campo all_sedi alla tabella user...")
            with db.engine.connect() as connection:
                connection.execute(db.text(
                    'ALTER TABLE "user" ADD COLUMN all_sedi BOOLEAN DEFAULT FALSE'
                ))
                
                # Imposta il valore di default per tutti gli utenti esistenti
                print("🔄 Impostazione valori di default per utenti esistenti...")
                connection.execute(db.text(
                    'UPDATE "user" SET all_sedi = FALSE WHERE all_sedi IS NULL'
                ))
                connection.commit()
            
            print("✅ Campo all_sedi aggiunto con successo!")
            return True
            
        except Exception as e:
            print(f"❌ Errore durante l'aggiunta del campo all_sedi: {e}")
            return False

if __name__ == '__main__':
    print("🚀 Avvio migrazione database...")
    success = add_all_sedi_field()
    if success:
        print("✅ Migrazione completata con successo!")
    else:
        print("❌ Migrazione fallita!")
        sys.exit(1)