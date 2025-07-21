#!/usr/bin/env python3
"""
Script per aggiornare i permessi dei ruoli esistenti con i nuovi permessi
per gestione/visualizzazione turni e reperibilità
"""

import sqlite3
import json
import os
import sys

def init_role_permissions_db():
    """Inizializza i permessi per i ruoli esistenti direttamente nel database"""
    
    # Usa DATABASE_URL se disponibile, altrimenti instance/database.db
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith('postgresql://'):
        import psycopg2
        return init_role_permissions_postgres()
    else:
        # Assumi SQLite per sviluppo
        db_path = 'instance/database.db'
        if not os.path.exists(db_path):
            print(f"Database non trovato: {db_path}")
            return False
        
        return init_role_permissions_sqlite(db_path)

def init_role_permissions_sqlite(db_path):
    """Inizializza permessi usando SQLite"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Verifica se la tabella UserRole esiste
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_role';")
    if not cursor.fetchone():
        print("Tabella user_role non trovata nel database")
        conn.close()
        return False
    
    print("Aggiornamento permessi ruoli...")
    
    # Definisci i permessi predefiniti per ogni ruolo
    role_permissions = {
        'Admin': {
            'can_manage_users': True,
            'can_manage_shifts': True,
            'can_view_shifts': True,
            'can_manage_reperibilita': True,
            'can_view_reperibilita': True,
            'can_approve_leave': True,
            'can_request_leave': False,
            'can_access_attendance': False,
            'can_access_dashboard': True,
            'can_view_reports': True,
            'can_manage_sedi': True,
            'can_manage_roles': True
        },
        'Staff': {
            'can_manage_users': False,
            'can_manage_shifts': False,
            'can_view_shifts': True,
            'can_manage_reperibilita': False,
            'can_view_reperibilita': True,
            'can_approve_leave': True,
            'can_request_leave': False,
            'can_access_attendance': False,
            'can_access_dashboard': True,
            'can_view_reports': True,
            'can_manage_sedi': False,
            'can_manage_roles': False
        },
        'Management': {
            'can_manage_users': False,
            'can_manage_shifts': True,
            'can_view_shifts': True,
            'can_manage_reperibilita': True,
            'can_view_reperibilita': True,
            'can_approve_leave': True,
            'can_request_leave': True,
            'can_access_attendance': True,
            'can_access_dashboard': True,
            'can_view_reports': True,
            'can_manage_sedi': False,
            'can_manage_roles': False
        },
        'Project Manager': {
            'can_manage_users': False,
            'can_manage_shifts': False,
            'can_view_shifts': True,
            'can_manage_reperibilita': False,
            'can_view_reperibilita': True,
            'can_approve_leave': False,
            'can_request_leave': False,
            'can_access_attendance': False,
            'can_access_dashboard': True,
            'can_view_reports': True,
            'can_manage_sedi': False,
            'can_manage_roles': False
        },
        'Redattore': {
            'can_manage_users': False,
            'can_manage_shifts': False,
            'can_view_shifts': True,
            'can_manage_reperibilita': False,
            'can_view_reperibilita': True,
            'can_approve_leave': False,
            'can_request_leave': True,
            'can_access_attendance': True,
            'can_access_dashboard': True,
            'can_view_reports': False,
            'can_manage_sedi': False,
            'can_manage_roles': False
        },
        'Sviluppatore': {
            'can_manage_users': False,
            'can_manage_shifts': False,
            'can_view_shifts': True,
            'can_manage_reperibilita': False,
            'can_view_reperibilita': True,
            'can_approve_leave': False,
            'can_request_leave': True,
            'can_access_attendance': True,
            'can_access_dashboard': True,
            'can_view_reports': False,
            'can_manage_sedi': False,
            'can_manage_roles': False
        },
        'Operatore': {
            'can_manage_users': False,
            'can_manage_shifts': False,
            'can_view_shifts': True,
            'can_manage_reperibilita': False,
            'can_view_reperibilita': True,
            'can_approve_leave': False,
            'can_request_leave': True,
            'can_access_attendance': True,
            'can_access_dashboard': True,
            'can_view_reports': False,
            'can_manage_sedi': False,
            'can_manage_roles': False
        },
        'Ente': {
            'can_manage_users': False,
            'can_manage_shifts': False,
            'can_view_shifts': False,
            'can_manage_reperibilita': False,
            'can_view_reperibilita': False,
            'can_approve_leave': False,
            'can_request_leave': False,
            'can_access_attendance': False,
            'can_access_dashboard': False,
            'can_view_reports': False,
            'can_manage_sedi': False,
            'can_manage_roles': False
        }
    }
    
    # Aggiorna o crea ruoli con permessi
    created_count = 0
    updated_count = 0
    
    for role_name, permissions in role_permissions.items():
        # Controlla se il ruolo esiste
        cursor.execute("SELECT id, permissions FROM user_role WHERE name = ?", (role_name,))
        existing_role = cursor.fetchone()
        
        permissions_json = json.dumps(permissions)
        
        if existing_role:
            # Aggiorna ruolo esistente
            cursor.execute(
                "UPDATE user_role SET permissions = ? WHERE name = ?", 
                (permissions_json, role_name)
            )
            updated_count += 1
            print(f"✓ Aggiornato ruolo: {role_name}")
        else:
            # Crea nuovo ruolo
            cursor.execute(
                """INSERT INTO user_role (name, display_name, description, permissions, active) 
                   VALUES (?, ?, ?, ?, ?)""",
                (role_name, role_name, f"Ruolo {role_name} con permessi configurati automaticamente", 
                 permissions_json, True)
            )
            created_count += 1
            print(f"✓ Creato ruolo: {role_name}")
    
    try:
        conn.commit()
        print(f"\nCompletato! {created_count} ruoli creati, {updated_count} ruoli aggiornati")
        
        # Mostra riepilogo permessi per verificare
        print("\n=== Riepilogo Permessi ===")
        for role_name in role_permissions.keys():
            cursor.execute("SELECT permissions FROM user_role WHERE name = ?", (role_name,))
            result = cursor.fetchone()
            if result:
                permissions = json.loads(result[0])
                turni_gestione = "✓" if permissions.get('can_manage_shifts', False) else "✗"
                turni_visual = "✓" if permissions.get('can_view_shifts', False) else "✗"
                rep_gestione = "✓" if permissions.get('can_manage_reperibilita', False) else "✗"
                rep_visual = "✓" if permissions.get('can_view_reperibilita', False) else "✗"
                
                print(f"{role_name:15} | Turni: Gestione {turni_gestione} Visual {turni_visual} | Reperibilità: Gestione {rep_gestione} Visual {rep_visual}")
                
    except Exception as e:
        conn.rollback()
        print(f"Errore durante il salvataggio: {e}")
        return False
    finally:
        conn.close()
        
    return True

def init_role_permissions_postgres():
    """Inizializza permessi usando PostgreSQL"""
    import psycopg2
    import psycopg2.extras
    
    db_url = os.environ.get('DATABASE_URL')
    
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        print("Aggiornamento permessi ruoli (PostgreSQL)...")
        
        # Stessi permessi di SQLite
        role_permissions = {
            'Admin': {
                'can_manage_users': True,
                'can_manage_shifts': True,
                'can_view_shifts': True,
                'can_manage_reperibilita': True,
                'can_view_reperibilita': True,
                'can_approve_leave': True,
                'can_request_leave': False,
                'can_access_attendance': False,
                'can_access_dashboard': True,
                'can_view_reports': True,
                'can_manage_sedi': True,
                'can_manage_roles': True
            },
            'Staff': {
                'can_manage_users': False,
                'can_manage_shifts': False,
                'can_view_shifts': True,
                'can_manage_reperibilita': False,
                'can_view_reperibilita': True,
                'can_approve_leave': True,
                'can_request_leave': False,
                'can_access_attendance': False,
                'can_access_dashboard': True,
                'can_view_reports': True,
                'can_manage_sedi': False,
                'can_manage_roles': False
            },
            'Management': {
                'can_manage_users': False,
                'can_manage_shifts': True,
                'can_view_shifts': True,
                'can_manage_reperibilita': True,
                'can_view_reperibilita': True,
                'can_approve_leave': True,
                'can_request_leave': True,
                'can_access_attendance': True,
                'can_access_dashboard': True,
                'can_view_reports': True,
                'can_manage_sedi': False,
                'can_manage_roles': False
            },
            'Project Manager': {
                'can_manage_users': False,
                'can_manage_shifts': False,
                'can_view_shifts': True,
                'can_manage_reperibilita': False,
                'can_view_reperibilita': True,
                'can_approve_leave': False,
                'can_request_leave': False,
                'can_access_attendance': False,
                'can_access_dashboard': True,
                'can_view_reports': True,
                'can_manage_sedi': False,
                'can_manage_roles': False
            },
            'Redattore': {
                'can_manage_users': False,
                'can_manage_shifts': False,
                'can_view_shifts': True,
                'can_manage_reperibilita': False,
                'can_view_reperibilita': True,
                'can_approve_leave': False,
                'can_request_leave': True,
                'can_access_attendance': True,
                'can_access_dashboard': True,
                'can_view_reports': False,
                'can_manage_sedi': False,
                'can_manage_roles': False
            },
            'Sviluppatore': {
                'can_manage_users': False,
                'can_manage_shifts': False,
                'can_view_shifts': True,
                'can_manage_reperibilita': False,
                'can_view_reperibilita': True,
                'can_approve_leave': False,
                'can_request_leave': True,
                'can_access_attendance': True,
                'can_access_dashboard': True,
                'can_view_reports': False,
                'can_manage_sedi': False,
                'can_manage_roles': False
            },
            'Operatore': {
                'can_manage_users': False,
                'can_manage_shifts': False,
                'can_view_shifts': True,
                'can_manage_reperibilita': False,
                'can_view_reperibilita': True,
                'can_approve_leave': False,
                'can_request_leave': True,
                'can_access_attendance': True,
                'can_access_dashboard': True,
                'can_view_reports': False,
                'can_manage_sedi': False,
                'can_manage_roles': False
            },
            'Ente': {
                'can_manage_users': False,
                'can_manage_shifts': False,
                'can_view_shifts': False,
                'can_manage_reperibilita': False,
                'can_view_reperibilita': False,
                'can_approve_leave': False,
                'can_request_leave': False,
                'can_access_attendance': False,
                'can_access_dashboard': False,
                'can_view_reports': False,
                'can_manage_sedi': False,
                'can_manage_roles': False
            }
        }
        
        # Aggiorna o crea ruoli con permessi
        created_count = 0
        updated_count = 0
        
        for role_name, permissions in role_permissions.items():
            # Controlla se il ruolo esiste
            cursor.execute("SELECT id, permissions FROM user_role WHERE name = %s", (role_name,))
            existing_role = cursor.fetchone()
            
            permissions_json = json.dumps(permissions)
            
            if existing_role:
                # Aggiorna ruolo esistente
                cursor.execute(
                    "UPDATE user_role SET permissions = %s WHERE name = %s", 
                    (permissions_json, role_name)
                )
                updated_count += 1
                print(f"✓ Aggiornato ruolo: {role_name}")
            else:
                # Crea nuovo ruolo
                cursor.execute(
                    """INSERT INTO user_role (name, display_name, description, permissions, active) 
                       VALUES (%s, %s, %s, %s, %s)""",
                    (role_name, role_name, f"Ruolo {role_name} con permessi configurati automaticamente", 
                     permissions_json, True)
                )
                created_count += 1
                print(f"✓ Creato ruolo: {role_name}")
        
        conn.commit()
        print(f"\nCompletato! {created_count} ruoli creati, {updated_count} ruoli aggiornati")
        
        # Mostra riepilogo permessi per verificare
        print("\n=== Riepilogo Permessi ===")
        for role_name in role_permissions.keys():
            cursor.execute("SELECT permissions FROM user_role WHERE name = %s", (role_name,))
            result = cursor.fetchone()
            if result:
                permissions_data = result['permissions']
                if isinstance(permissions_data, str):
                    permissions = json.loads(permissions_data)
                else:
                    permissions = permissions_data
                turni_gestione = "✓" if permissions.get('can_manage_shifts', False) else "✗"
                turni_visual = "✓" if permissions.get('can_view_shifts', False) else "✗"
                rep_gestione = "✓" if permissions.get('can_manage_reperibilita', False) else "✗"
                rep_visual = "✓" if permissions.get('can_view_reperibilita', False) else "✗"
                
                print(f"{role_name:15} | Turni: Gestione {turni_gestione} Visual {turni_visual} | Reperibilità: Gestione {rep_gestione} Visual {rep_visual}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Errore PostgreSQL: {e}")
        return False

def init_role_permissions():
    """Funzione principale per inizializzare i permessi"""
    return init_role_permissions_db()

if __name__ == '__main__':
    success = init_role_permissions()
    sys.exit(0 if success else 1)

def init_role_permissions():
    """Inizializza i permessi per i ruoli esistenti"""
    with app.app_context():
        print("Aggiornamento permessi ruoli...")
        
        # Definisci i permessi predefiniti per ogni ruolo
        role_permissions = {
            'Admin': {
                'can_manage_users': True,
                'can_manage_shifts': True,
                'can_view_shifts': True,
                'can_manage_reperibilita': True,
                'can_view_reperibilita': True,
                'can_approve_leave': True,
                'can_request_leave': False,
                'can_access_attendance': False,
                'can_access_dashboard': True,
                'can_view_reports': True,
                'can_manage_sedi': True,
                'can_manage_roles': True
            },
            'Staff': {
                'can_manage_users': False,
                'can_manage_shifts': False,
                'can_view_shifts': True,
                'can_manage_reperibilita': False,
                'can_view_reperibilita': True,
                'can_approve_leave': True,
                'can_request_leave': False,
                'can_access_attendance': False,
                'can_access_dashboard': True,
                'can_view_reports': True,
                'can_manage_sedi': False,
                'can_manage_roles': False
            },
            'Management': {
                'can_manage_users': False,
                'can_manage_shifts': True,
                'can_view_shifts': True,
                'can_manage_reperibilita': True,
                'can_view_reperibilita': True,
                'can_approve_leave': True,
                'can_request_leave': True,
                'can_access_attendance': True,
                'can_access_dashboard': True,
                'can_view_reports': True,
                'can_manage_sedi': False,
                'can_manage_roles': False
            },
            'Project Manager': {
                'can_manage_users': False,
                'can_manage_shifts': False,
                'can_view_shifts': True,
                'can_manage_reperibilita': False,
                'can_view_reperibilita': True,
                'can_approve_leave': False,
                'can_request_leave': False,
                'can_access_attendance': False,
                'can_access_dashboard': True,
                'can_view_reports': True,
                'can_manage_sedi': False,
                'can_manage_roles': False
            },
            'Redattore': {
                'can_manage_users': False,
                'can_manage_shifts': False,
                'can_view_shifts': True,
                'can_manage_reperibilita': False,
                'can_view_reperibilita': True,
                'can_approve_leave': False,
                'can_request_leave': True,
                'can_access_attendance': True,
                'can_access_dashboard': True,
                'can_view_reports': False,
                'can_manage_sedi': False,
                'can_manage_roles': False
            },
            'Sviluppatore': {
                'can_manage_users': False,
                'can_manage_shifts': False,
                'can_view_shifts': True,
                'can_manage_reperibilita': False,
                'can_view_reperibilita': True,
                'can_approve_leave': False,
                'can_request_leave': True,
                'can_access_attendance': True,
                'can_access_dashboard': True,
                'can_view_reports': False,
                'can_manage_sedi': False,
                'can_manage_roles': False
            },
            'Operatore': {
                'can_manage_users': False,
                'can_manage_shifts': False,
                'can_view_shifts': True,
                'can_manage_reperibilita': False,
                'can_view_reperibilita': True,
                'can_approve_leave': False,
                'can_request_leave': True,
                'can_access_attendance': True,
                'can_access_dashboard': True,
                'can_view_reports': False,
                'can_manage_sedi': False,
                'can_manage_roles': False
            },
            'Ente': {
                'can_manage_users': False,
                'can_manage_shifts': False,
                'can_view_shifts': False,
                'can_manage_reperibilita': False,
                'can_view_reperibilita': False,
                'can_approve_leave': False,
                'can_request_leave': False,
                'can_access_attendance': False,
                'can_access_dashboard': False,
                'can_view_reports': False,
                'can_manage_sedi': False,
                'can_manage_roles': False
            }
        }
        
        # Aggiorna o crea ruoli con permessi
        created_count = 0
        updated_count = 0
        
        for role_name, permissions in role_permissions.items():
            role = UserRole.query.filter_by(name=role_name).first()
            
            if not role:
                # Crea nuovo ruolo
                role = UserRole(
                    name=role_name,
                    display_name=role_name,
                    description=f"Ruolo {role_name} con permessi configurati automaticamente",
                    permissions=permissions,
                    active=True
                )
                db.session.add(role)
                created_count += 1
                print(f"✓ Creato ruolo: {role_name}")
            else:
                # Aggiorna permessi esistenti
                role.permissions = permissions
                updated_count += 1
                print(f"✓ Aggiornato ruolo: {role_name}")
        
        try:
            db.session.commit()
            print(f"\nCompletato! {created_count} ruoli creati, {updated_count} ruoli aggiornati")
            
            # Mostra riepilogo permessi per verificare
            print("\n=== Riepilogo Permessi ===")
            for role_name in role_permissions.keys():
                role = UserRole.query.filter_by(name=role_name).first()
                if role:
                    turni_gestione = "✓" if role.has_permission('can_manage_shifts') else "✗"
                    turni_visual = "✓" if role.has_permission('can_view_shifts') else "✗"
                    rep_gestione = "✓" if role.has_permission('can_manage_reperibilita') else "✗"
                    rep_visual = "✓" if role.has_permission('can_view_reperibilita') else "✗"
                    
                    print(f"{role_name:15} | Turni: Gestione {turni_gestione} Visual {turni_visual} | Reperibilità: Gestione {rep_gestione} Visual {rep_visual}")
                    
        except Exception as e:
            db.session.rollback()
            print(f"Errore durante il salvataggio: {e}")
            return False
            
        return True

if __name__ == '__main__':
    success = init_role_permissions()
    sys.exit(0 if success else 1)