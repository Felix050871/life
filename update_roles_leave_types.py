#!/usr/bin/env python3
"""
Script per aggiungere il permesso can_manage_leave_types ai ruoli esistenti.
Solo l'Amministratore dovrebbe avere questo permesso per gestire le tipologie.
"""

from app import app, db
from models import UserRole
import json

def update_roles_leave_types():
    """Aggiunge il permesso can_manage_leave_types ai ruoli appropriati"""
    with app.app_context():
        try:
            # Ottieni tutti i ruoli
            roles = UserRole.query.all()
            updated_count = 0
            
            for role in roles:
                # Ottieni i permessi attuali come dizionario
                current_permissions = role.get_permissions_dict()
                
                # Solo l'Amministratore dovrebbe poter gestire le tipologie di permesso
                if role.name == 'Amministratore':
                    if not current_permissions.get('can_manage_leave_types', False):
                        current_permissions['can_manage_leave_types'] = True
                        role.permissions = json.dumps(current_permissions)
                        updated_count += 1
                        print(f"✓ Aggiunto permesso can_manage_leave_types al ruolo: Amministratore")
                    else:
                        print(f"- Il ruolo Amministratore ha già il permesso can_manage_leave_types")
                else:
                    # Altri ruoli non dovrebbero avere questo permesso (a meno che non sia stato aggiunto manualmente)
                    if current_permissions.get('can_manage_leave_types', False):
                        print(f"- Il ruolo {role.name} ha già il permesso can_manage_leave_types (mantenuto)")
                    else:
                        current_permissions['can_manage_leave_types'] = False
                        role.permissions = json.dumps(current_permissions)
                        print(f"- Permesso can_manage_leave_types impostato su False per: {role.name}")
            
            if updated_count > 0:
                db.session.commit()
                print(f"\n✅ Aggiornamento completato! {updated_count} ruoli modificati.")
            else:
                print("\n✅ Tutti i ruoli sono già aggiornati correttamente.")
            
            # Verifica finale
            print("\nStato finale dei permessi:")
            for role in UserRole.query.all():
                permissions = role.get_permissions_dict()
                has_permission = permissions.get('can_manage_leave_types', False)
                status = "✓" if has_permission else "✗"
                print(f"  {status} {role.name}: {'Può gestire tipologie' if has_permission else 'Non può gestire tipologie'}")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ Errore durante l'aggiornamento: {e}")
            raise

if __name__ == '__main__':
    update_roles_leave_types()