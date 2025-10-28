#!/usr/bin/env python3
"""
Script per popolare le tipologie di presenza di default per tutte le company
"""

from app import app, db
from models import Company, AttendanceType

def populate_attendance_types():
    """Popola le tipologie di presenza di default per tutte le company"""
    
    default_types = [
        {
            'name': 'Ordinario',
            'description': 'Lavoro ordinario in sede',
            'is_default': True,
            'active': True
        },
        {
            'name': 'Trasferta nazionale',
            'description': 'Trasferta su territorio nazionale',
            'is_default': False,
            'active': True
        },
        {
            'name': 'Trasferta internazionale',
            'description': 'Trasferta su territorio internazionale',
            'is_default': False,
            'active': True
        }
    ]
    
    with app.app_context():
        companies = Company.query.all()
        
        if not companies:
            print("⚠️  Nessuna company trovata nel database")
            return
        
        for company in companies:
            print(f"\n📋 Popolo tipologie per company: {company.name} (ID: {company.id})")
            
            for type_data in default_types:
                # Verifica se la tipologia esiste già per questa company
                existing = AttendanceType.query.filter_by(
                    company_id=company.id,
                    name=type_data['name']
                ).first()
                
                if existing:
                    print(f"   ⏭️  Tipologia '{type_data['name']}' già esistente, skip")
                    continue
                
                # Crea la nuova tipologia
                new_type = AttendanceType(
                    name=type_data['name'],
                    description=type_data['description'],
                    is_default=type_data['is_default'],
                    active=type_data['active'],
                    company_id=company.id,
                    created_by=None  # Creato dal sistema
                )
                
                db.session.add(new_type)
                print(f"   ✅ Creata tipologia: {type_data['name']}")
            
        try:
            db.session.commit()
            print("\n✨ Tipologie di presenza popolate con successo!\n")
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Errore durante il salvataggio: {str(e)}\n")
            raise

if __name__ == '__main__':
    populate_attendance_types()
