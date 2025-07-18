#!/usr/bin/env python3
"""
Script per precariccare le festività nazionali italiane
"""

from app import app, db
from models import Holiday, User

def init_national_holidays():
    """Precarica le festività nazionali italiane"""
    
    # Festività nazionali italiane fisse
    national_holidays = [
        {"name": "Capodanno", "day": 1, "month": 1, "description": "Primo giorno dell'anno"},
        {"name": "Epifania", "day": 6, "month": 1, "description": "Befana"},
        {"name": "Festa della Liberazione", "day": 25, "month": 4, "description": "Anniversario della Liberazione"},
        {"name": "Festa del Lavoro", "day": 1, "month": 5, "description": "Festa dei Lavoratori"},
        {"name": "Festa della Repubblica", "day": 2, "month": 6, "description": "Festa Nazionale della Repubblica Italiana"},
        {"name": "Ferragosto", "day": 15, "month": 8, "description": "Assunzione di Maria Vergine"},
        {"name": "Ognissanti", "day": 1, "month": 11, "description": "Festa di Tutti i Santi"},
        {"name": "Immacolata Concezione", "day": 8, "month": 12, "description": "Immacolata Concezione"},
        {"name": "Natale", "day": 25, "month": 12, "description": "Natività di Gesù"},
        {"name": "Santo Stefano", "day": 26, "month": 12, "description": "Primo giorno dopo Natale"},
    ]
    
    with app.app_context():
        # Trova un utente Admin per essere il creatore
        admin_user = User.query.filter_by(role='Admin').first()
        if not admin_user:
            print("Nessun utente Admin trovato. Creando le festività senza creatore.")
            return
        
        created_count = 0
        
        for holiday_data in national_holidays:
            # Verifica se la festività esiste già
            existing = Holiday.query.filter_by(
                name=holiday_data["name"],
                day=holiday_data["day"],
                month=holiday_data["month"],
                sede_id=None  # Nazionale
            ).first()
            
            if not existing:
                holiday = Holiday(
                    name=holiday_data["name"],
                    day=holiday_data["day"],
                    month=holiday_data["month"],
                    sede_id=None,  # Nazionale
                    description=holiday_data["description"],
                    is_active=True,
                    created_by=admin_user.id
                )
                
                db.session.add(holiday)
                created_count += 1
                print(f"Aggiunta festività: {holiday_data['name']} ({holiday_data['day']}/{holiday_data['month']})")
            else:
                print(f"Festività già esistente: {holiday_data['name']} ({holiday_data['day']}/{holiday_data['month']})")
        
        if created_count > 0:
            db.session.commit()
            print(f"\nPrecaricate {created_count} festività nazionali italiane!")
        else:
            print("\nTutte le festività nazionali sono già presenti nel database.")

if __name__ == "__main__":
    init_national_holidays()