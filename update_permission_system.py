#!/usr/bin/env python3
"""
Script per aggiornare il sistema dei permessi - Standardizzazione completa
Aggiunge i permessi "my" mancanti a tutti i ruoli esistenti
"""
import json
import os
import psycopg2
from flask import Flask
from app import app

# Mapping dei permessi da standardizzare
PERMISSION_MAPPINGS = {
    # Se ha il permesso generale, dovrebbe avere anche quello personale
    'can_view_reperibilita': 'can_view_my_reperibilita',
    'can_view_attendance': 'can_view_my_attendance', 
    'can_view_leave': 'can_view_my_leave'
}

def update_permissions():
    """Aggiorna tutti i ruoli per includere i nuovi permessi standardizzati"""
    
    with app.app_context():
        # Connettiti al database
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        cur = conn.cursor()

        print("=== AGGIORNAMENTO SISTEMA PERMESSI ===")
        
        try:
            # Preleva tutti i ruoli
            cur.execute('SELECT name, permissions FROM user_role')
            roles = cur.fetchall()

            for role_name, permissions_data in roles:
                print(f'\n--- Ruolo: {role_name} ---')
                # PostgreSQL restituisce già un dict, non serve json.loads()
                if isinstance(permissions_data, str):
                    permissions = json.loads(permissions_data)
                else:
                    permissions = permissions_data
                updated = False
                
                # Aggiungi i nuovi permessi mancanti
                for general_perm, personal_perm in PERMISSION_MAPPINGS.items():
                    if personal_perm not in permissions:
                        # Se ha il permesso generale, dai anche quello personale
                        if permissions.get(general_perm, False):
                            permissions[personal_perm] = True
                            print(f"✓ Aggiunto {personal_perm} = true (basato su {general_perm})")
                            updated = True
                        else:
                            # Altrimenti impostalo come false per default
                            permissions[personal_perm] = False
                            print(f"• Aggiunto {personal_perm} = false (default)")
                            updated = True
                    else:
                        print(f"- {personal_perm} già presente")

                # Aggiorna il database se ci sono state modifiche
                if updated:
                    new_permissions_str = json.dumps(permissions, separators=(',', ':'))
                    cur.execute('UPDATE user_role SET permissions = %s WHERE name = %s', 
                              (new_permissions_str, role_name))
                    print(f"✓ Database aggiornato per {role_name}")
                else:
                    print("• Nessun aggiornamento necessario")

            conn.commit()
            print("\n✅ AGGIORNAMENTO COMPLETATO CON SUCCESSO")
            
        except Exception as e:
            conn.rollback()
            print(f"\n❌ ERRORE: {e}")
            
        finally:
            cur.close()
            conn.close()

if __name__ == '__main__':
    update_permissions()