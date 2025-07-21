#!/usr/bin/env python3
"""
Script per aggiornare tutti i ruoli con permessi granulari completi
Elimina i riferimenti ai vecchi ruoli (Redattore, PM, Ente, ecc)
"""

import sqlite3
import json
import os
import sys

def get_all_available_permissions():
    """Restituisce tutti i permessi disponibili nel sistema"""
    return [
        # HOME
        'can_access_dashboard',
        
        # RUOLI  
        'can_manage_roles',
        'can_view_roles',
        
        # UTENTI
        'can_manage_users',
        'can_view_users',
        
        # SEDI
        'can_manage_sedi',
        'can_view_sedi',
        
        # ORARI
        'can_manage_schedules',
        'can_view_schedules',
        
        # TURNI
        'can_manage_shifts',
        'can_view_shifts',
        
        # REPERIBILITÀ
        'can_manage_reperibilita',
        'can_view_reperibilita',
        
        # PRESENZE
        'can_manage_attendance',
        'can_view_attendance',
        'can_access_attendance',
        
        # FERIE/PERMESSI
        'can_manage_leave',
        'can_approve_leave',
        'can_request_leave',
        'can_view_leave',
        
        # INTERVENTI
        'can_manage_interventions',
        'can_view_interventions',
        
        # FESTIVITÀ
        'can_manage_holidays',
        'can_view_holidays',
        
        # GESTIONE QR
        'can_manage_qr',
        'can_view_qr',
        
        # STATISTICHE
        'can_view_reports',
        'can_manage_reports',
        
        # MESSAGGI
        'can_send_messages',
        'can_view_messages'
    ]

def update_granular_permissions_db():
    """Aggiorna tutti i ruoli con permessi granulari"""
    
    # Usa DATABASE_URL se disponibile, altrimenti instance/database.db
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith('postgresql://'):
        import psycopg2
        return update_granular_permissions_postgres()
    else:
        # Assumi SQLite per sviluppo
        db_path = 'instance/database.db'
        if not os.path.exists(db_path):
            print(f"Database non trovato: {db_path}")
            return False
        
        return update_granular_permissions_sqlite(db_path)

def update_granular_permissions_postgres():
    """Aggiorna permessi usando PostgreSQL"""
    import psycopg2
    import psycopg2.extras
    
    db_url = os.environ.get('DATABASE_URL')
    
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        print("Aggiornamento con permessi granulari (PostgreSQL)...")
        
        # Nuovi ruoli con permessi granulari (eliminati vecchi ruoli)
        new_roles = {
            'Amministratore': {
                'description': 'Amministratore del sistema con accesso completo',
                'permissions': {perm: True for perm in get_all_available_permissions()}
            },
            'Responsabile': {
                'description': 'Responsabile locale con gestione operativa sede',
                'permissions': {
                    'can_access_dashboard': True,
                    'can_view_users': True,
                    'can_view_sedi': True,
                    'can_view_schedules': True,
                    'can_manage_shifts': True,
                    'can_view_shifts': True,
                    'can_manage_reperibilita': True,
                    'can_view_reperibilita': True,
                    'can_manage_attendance': True,
                    'can_view_attendance': True,
                    'can_access_attendance': True,
                    'can_manage_leave': True,
                    'can_approve_leave': True,
                    'can_request_leave': True,
                    'can_view_leave': True,
                    'can_manage_interventions': True,
                    'can_view_interventions': True,
                    'can_view_holidays': True,
                    'can_view_reports': True,
                    'can_send_messages': True,
                    'can_view_messages': True
                }
            },
            'Supervisore': {
                'description': 'Supervisore globale con accesso a tutte le sedi (sola visualizzazione)',
                'permissions': {
                    'can_access_dashboard': True,
                    'can_view_users': True,
                    'can_view_sedi': True,
                    'can_view_schedules': True,
                    'can_view_shifts': True,
                    'can_view_reperibilita': True,
                    'can_view_attendance': True,
                    'can_approve_leave': True,
                    'can_view_leave': True,
                    'can_view_interventions': True,
                    'can_view_holidays': True,
                    'can_view_reports': True,
                    'can_send_messages': True,
                    'can_view_messages': True
                }
            },
            'Operatore': {
                'description': 'Operatore standard con accesso alle funzioni operative',
                'permissions': {
                    'can_access_dashboard': True,
                    'can_view_shifts': True,
                    'can_view_reperibilita': True,
                    'can_access_attendance': True,
                    'can_request_leave': True,
                    'can_view_leave': True,
                    'can_view_interventions': True,
                    'can_view_holidays': True
                }
            },
            'Ospite': {
                'description': 'Accesso limitato solo per visualizzazione',
                'permissions': {
                    'can_access_dashboard': False,
                    'can_view_attendance': True
                }
            }
        }
        
        # Prima, elimina i vecchi ruoli se esistono
        old_roles = ['Admin', 'Staff', 'Management', 'Project Manager', 'Redattore', 'Sviluppatore', 'Operatore', 'Ente']
        for old_role in old_roles:
            # Aggiorna gli utenti che hanno il vecchio ruolo per usare un nuovo ruolo
            if old_role == 'Admin':
                cursor.execute("UPDATE \"user\" SET role = %s WHERE role = %s", ('Amministratore', old_role))
            elif old_role in ['Management']:
                cursor.execute("UPDATE \"user\" SET role = %s WHERE role = %s", ('Responsabile', old_role))
            elif old_role in ['Staff']:
                cursor.execute("UPDATE \"user\" SET role = %s WHERE role = %s", ('Supervisore', old_role))
            elif old_role in ['Redattore', 'Sviluppatore', 'Operatore']:
                cursor.execute("UPDATE \"user\" SET role = %s WHERE role = %s", ('Operatore', old_role))
            elif old_role in ['Project Manager', 'Ente']:
                cursor.execute("UPDATE \"user\" SET role = %s WHERE role = %s", ('Ospite', old_role))
            
            # Elimina il vecchio ruolo dalla tabella user_role
            cursor.execute("DELETE FROM user_role WHERE name = %s", (old_role,))
        
        # Crea i nuovi ruoli
        created_count = 0
        updated_count = 0
        
        for role_name, role_data in new_roles.items():
            # Controlla se il ruolo esiste
            cursor.execute("SELECT id FROM user_role WHERE name = %s", (role_name,))
            existing_role = cursor.fetchone()
            
            permissions_json = json.dumps(role_data['permissions'])
            
            if existing_role:
                # Aggiorna ruolo esistente
                cursor.execute(
                    "UPDATE user_role SET display_name = %s, description = %s, permissions = %s, active = %s WHERE name = %s", 
                    (role_name, role_data['description'], permissions_json, True, role_name)
                )
                updated_count += 1
                print(f"✓ Aggiornato ruolo: {role_name}")
            else:
                # Crea nuovo ruolo
                cursor.execute(
                    """INSERT INTO user_role (name, display_name, description, permissions, active) 
                       VALUES (%s, %s, %s, %s, %s)""",
                    (role_name, role_name, role_data['description'], permissions_json, True)
                )
                created_count += 1
                print(f"✓ Creato ruolo: {role_name}")
        
        conn.commit()
        print(f"\nCompletato! {created_count} ruoli creati, {updated_count} ruoli aggiornati")
        print("Vecchi ruoli eliminati e utenti migrati ai nuovi ruoli")
        
        # Mostra riepilogo permessi principali
        print("\n=== Riepilogo Permessi Principali ===")
        for role_name in new_roles.keys():
            cursor.execute("SELECT permissions FROM user_role WHERE name = %s", (role_name,))
            result = cursor.fetchone()
            if result:
                permissions_data = result['permissions']
                if isinstance(permissions_data, str):
                    permissions = json.loads(permissions_data)
                else:
                    permissions = permissions_data
                
                # Conta i permessi attivi
                active_perms = sum(1 for v in permissions.values() if v)
                total_perms = len(permissions)
                
                # Permessi chiave
                admin_perms = "✓" if permissions.get('can_manage_users', False) else "✗"
                turni_perms = "✓" if permissions.get('can_manage_shifts', False) else "✗"
                rep_perms = "✓" if permissions.get('can_manage_reperibilita', False) else "✗"
                
                print(f"{role_name:15} | Permessi: {active_perms:2}/{total_perms} | Admin: {admin_perms} | Turni: {turni_perms} | Reperibilità: {rep_perms}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Errore PostgreSQL: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def update_granular_permissions_sqlite(db_path):
    """Aggiorna permessi usando SQLite"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Aggiornamento con permessi granulari (SQLite)...")
    
    # Usa la stessa logica di PostgreSQL ma con sintassi SQLite
    new_roles = {
        'Amministratore': {
            'description': 'Amministratore del sistema con accesso completo',
            'permissions': {perm: True for perm in get_all_available_permissions()}
        },
        'Responsabile': {
            'description': 'Responsabile locale con gestione operativa sede',
            'permissions': {
                'can_access_dashboard': True,
                'can_view_users': True,
                'can_view_sedi': True,
                'can_view_schedules': True,
                'can_manage_shifts': True,
                'can_view_shifts': True,
                'can_manage_reperibilita': True,
                'can_view_reperibilita': True,
                'can_manage_attendance': True,
                'can_view_attendance': True,
                'can_access_attendance': True,
                'can_manage_leave': True,
                'can_approve_leave': True,
                'can_request_leave': True,
                'can_view_leave': True,
                'can_manage_interventions': True,
                'can_view_interventions': True,
                'can_view_holidays': True,
                'can_view_reports': True,
                'can_send_messages': True,
                'can_view_messages': True
            }
        },
        'Supervisore': {
            'description': 'Supervisore globale con accesso a tutte le sedi (sola visualizzazione)',
            'permissions': {
                'can_access_dashboard': True,
                'can_view_users': True,
                'can_view_sedi': True,
                'can_view_schedules': True,
                'can_view_shifts': True,
                'can_view_reperibilita': True,
                'can_view_attendance': True,
                'can_approve_leave': True,
                'can_view_leave': True,
                'can_view_interventions': True,
                'can_view_holidays': True,
                'can_view_reports': True,
                'can_send_messages': True,
                'can_view_messages': True
            }
        },
        'Operatore': {
            'description': 'Operatore standard con accesso alle funzioni operative',
            'permissions': {
                'can_access_dashboard': True,
                'can_view_shifts': True,
                'can_view_reperibilita': True,
                'can_access_attendance': True,
                'can_request_leave': True,
                'can_view_leave': True,
                'can_view_interventions': True,
                'can_view_holidays': True
            }
        },
        'Ospite': {
            'description': 'Accesso limitato solo per visualizzazione',
            'permissions': {
                'can_access_dashboard': False,
                'can_view_attendance': True
            }
        }
    }
    
    try:
        # Migra utenti dai vecchi ruoli ai nuovi
        old_roles = ['Admin', 'Staff', 'Management', 'Project Manager', 'Redattore', 'Sviluppatore', 'Operatore', 'Ente']
        for old_role in old_roles:
            if old_role == 'Admin':
                cursor.execute("UPDATE user SET role = ? WHERE role = ?", ('Amministratore', old_role))
            elif old_role in ['Management']:
                cursor.execute("UPDATE user SET role = ? WHERE role = ?", ('Responsabile', old_role))
            elif old_role in ['Staff']:
                cursor.execute("UPDATE user SET role = ? WHERE role = ?", ('Supervisore', old_role))
            elif old_role in ['Redattore', 'Sviluppatore', 'Operatore']:
                cursor.execute("UPDATE user SET role = ? WHERE role = ?", ('Operatore', old_role))
            elif old_role in ['Project Manager', 'Ente']:
                cursor.execute("UPDATE user SET role = ? WHERE role = ?", ('Ospite', old_role))
            
            # Elimina il vecchio ruolo
            cursor.execute("DELETE FROM user_role WHERE name = ?", (old_role,))
        
        # Crea i nuovi ruoli
        created_count = 0
        updated_count = 0
        
        for role_name, role_data in new_roles.items():
            cursor.execute("SELECT id FROM user_role WHERE name = ?", (role_name,))
            existing_role = cursor.fetchone()
            
            permissions_json = json.dumps(role_data['permissions'])
            
            if existing_role:
                cursor.execute(
                    "UPDATE user_role SET display_name = ?, description = ?, permissions = ?, active = ? WHERE name = ?", 
                    (role_name, role_data['description'], permissions_json, True, role_name)
                )
                updated_count += 1
                print(f"✓ Aggiornato ruolo: {role_name}")
            else:
                cursor.execute(
                    """INSERT INTO user_role (name, display_name, description, permissions, active) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (role_name, role_name, role_data['description'], permissions_json, True)
                )
                created_count += 1
                print(f"✓ Creato ruolo: {role_name}")
        
        conn.commit()
        print(f"\nCompletato! {created_count} ruoli creati, {updated_count} ruoli aggiornati")
        print("Vecchi ruoli eliminati e utenti migrati ai nuovi ruoli")
        
        conn.close()
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"Errore durante l'aggiornamento: {e}")
        conn.close()
        return False

if __name__ == '__main__':
    success = update_granular_permissions_db()
    sys.exit(0 if success else 1)