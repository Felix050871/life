#!/usr/bin/env python3
"""
Migration script per aggiungere i campi start_time ed end_time alla tabella leave_request
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import LeaveRequest

def migrate_leave_request_table():
    """Aggiunge i campi start_time ed end_time alla tabella leave_request"""
    with app.app_context():
        try:
            # Verifica se i campi esistono già
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('leave_request')]
            
            if 'start_time' not in columns:
                print("Aggiunta colonna start_time...")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE leave_request ADD COLUMN start_time TIME NULL"))
                    conn.commit()
                
            if 'end_time' not in columns:
                print("Aggiunta colonna end_time...")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE leave_request ADD COLUMN end_time TIME NULL"))
                    conn.commit()
                
            print("Migrazione completata con successo!")
            
        except Exception as e:
            print(f"Errore durante la migrazione: {e}")
            return False
            
    return True

if __name__ == '__main__':
    migrate_leave_request_table()