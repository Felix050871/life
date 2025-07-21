#!/usr/bin/env python3
"""
Script per migrare le coperture esistenti dal formato lista al formato dizionario
con numerosità di default = 1
"""

from app import app, db
from models import PresidioCoverage
import json

def migrate_coverage_roles():
    """Migra tutte le coperture dal formato lista al formato dizionario"""
    with app.app_context():
        # Trova tutte le coperture con required_roles non vuoto
        coperture = PresidioCoverage.query.filter(
            PresidioCoverage.required_roles.isnot(None),
            PresidioCoverage.required_roles != ''
        ).all()
        
        migrated_count = 0
        error_count = 0
        
        for copertura in coperture:
            try:
                # Prova a parsare il JSON
                data = json.loads(copertura.required_roles)
                
                # Se è una lista, convertila in dizionario
                if isinstance(data, list):
                    new_dict = {role: 1 for role in data}
                    copertura.required_roles = json.dumps(new_dict)
                    migrated_count += 1
                    print(f"Migrata copertura ID {copertura.id}: {data} -> {new_dict}")
                
                # Se è già un dizionario, non fare nulla
                elif isinstance(data, dict):
                    print(f"Copertura ID {copertura.id} già in formato dizionario: {data}")
                
                else:
                    print(f"Formato sconosciuto per copertura ID {copertura.id}: {data}")
                    error_count += 1
                    
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Errore parsing copertura ID {copertura.id}: {e}")
                # Prova a trattare come stringa singola
                if copertura.required_roles and isinstance(copertura.required_roles, str):
                    # Se sembra essere un singolo ruolo, crealo come dizionario
                    single_role_dict = {copertura.required_roles: 1}
                    copertura.required_roles = json.dumps(single_role_dict)
                    migrated_count += 1
                    print(f"Convertito ruolo singolo ID {copertura.id}: {copertura.required_roles} -> {single_role_dict}")
                else:
                    error_count += 1
        
        # Salva le modifiche
        if migrated_count > 0:
            db.session.commit()
            print(f"\n✅ Migrazione completata!")
            print(f"   - Coperture migrate: {migrated_count}")
            print(f"   - Errori: {error_count}")
            print(f"   - Totale processate: {len(coperture)}")
        else:
            print("\n📋 Nessuna copertura da migrare")

if __name__ == "__main__":
    migrate_coverage_roles()