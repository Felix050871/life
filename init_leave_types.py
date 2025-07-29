#!/usr/bin/env python3
"""
Script per inizializzare le tipologie di permesso predefinite nel database.
Eseguire questo script per popolare la tabella LeaveType con i dati iniziali.
"""

from app import app, db
from models import LeaveType

def init_leave_types():
    """Inizializza le tipologie di permesso predefinite"""
    with app.app_context():
        # Controlla se ci sono già tipologie esistenti
        existing_count = LeaveType.query.count()
        if existing_count > 0:
            print(f"Trovate {existing_count} tipologie esistenti. Aggiungendo solo quelle mancanti...")
        
        # Ottieni le tipologie predefinite
        default_types = LeaveType.get_default_types()
        added_count = 0
        
        for type_data in default_types:
            # Controlla se la tipologia esiste già
            existing = LeaveType.query.filter_by(name=type_data['name']).first()
            if not existing:
                leave_type = LeaveType(
                    name=type_data['name'],
                    description=type_data['description'],
                    requires_approval=type_data['requires_approval'],
                    is_active=True
                )
                db.session.add(leave_type)
                added_count += 1
                print(f"✓ Aggiunta tipologia: {type_data['name']}")
            else:
                print(f"- Tipologia già esistente: {type_data['name']}")
        
        if added_count > 0:
            db.session.commit()
            print(f"\n✅ Inizializzazione completata! Aggiunte {added_count} nuove tipologie di permesso.")
        else:
            print("\n✅ Tutte le tipologie predefinite sono già presenti nel database.")
        
        # Mostra il riepilogo finale
        total_types = LeaveType.query.count()
        print(f"\nTotale tipologie nel database: {total_types}")
        
        # Mostra l'elenco completo
        all_types = LeaveType.query.order_by(LeaveType.name).all()
        print("\nTipologie configurate:")
        for leave_type in all_types:
            approval_status = "Richiesta autorizzazione" if leave_type.requires_approval else "Auto-approvata"
            status = "Attiva" if leave_type.is_active else "Inattiva"
            print(f"  • {leave_type.name} - {approval_status} - {status}")

if __name__ == '__main__':
    init_leave_types()