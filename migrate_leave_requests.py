#!/usr/bin/env python3
"""
Script per migrare la tabella leave_request al nuovo sistema con tipologie configurabili.
Aggiunge la colonna leave_type_id e popola i dati esistenti.
"""

from app import app, db
from models import LeaveRequest, LeaveType
from sqlalchemy import text

def migrate_leave_requests():
    """Migra la tabella leave_request al nuovo sistema"""
    with app.app_context():
        try:
            # 1. Controlla se la colonna leave_type_id esiste già
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='leave_request' AND column_name='leave_type_id';
            """))
            
            if result.fetchone():
                print("✓ La colonna leave_type_id esiste già.")
                return
            
            print("🔄 Aggiungendo colonna leave_type_id alla tabella leave_request...")
            
            # 2. Aggiungi la colonna leave_type_id (nullable per ora)
            db.session.execute(text("""
                ALTER TABLE leave_request 
                ADD COLUMN leave_type_id INTEGER;
            """))
            
            # 3. Aggiungi la foreign key constraint
            db.session.execute(text("""
                ALTER TABLE leave_request 
                ADD CONSTRAINT fk_leave_request_leave_type_id 
                FOREIGN KEY (leave_type_id) REFERENCES leave_type (id);
            """))
            
            db.session.commit()
            print("✓ Colonna leave_type_id aggiunta con successo.")
            
            # 4. Popola la colonna leave_type_id con i dati esistenti
            print("🔄 Popolando leave_type_id per i record esistenti...")
            
            # Crea un mapping dai nomi vecchi a nuovi
            type_mapping = {
                'Ferie': 'Ferie',
                'Permesso': 'Permesso retribuito',
                'Malattia': 'Permesso per malattia del dipendente'
            }
            
            updated_count = 0
            for old_type, new_type in type_mapping.items():
                # Trova la tipologia corrispondente
                leave_type = LeaveType.query.filter_by(name=new_type).first()
                if leave_type:
                    # Aggiorna tutti i record con il vecchio tipo
                    result = db.session.execute(text("""
                        UPDATE leave_request 
                        SET leave_type_id = :leave_type_id 
                        WHERE leave_type = :old_type AND leave_type_id IS NULL
                    """), {
                        'leave_type_id': leave_type.id,
                        'old_type': old_type
                    })
                    count = result.rowcount
                    updated_count += count
                    print(f"  • {count} record aggiornati: '{old_type}' -> '{new_type}' (ID: {leave_type.id})")
                else:
                    print(f"  ⚠️ Tipologia non trovata: {new_type}")
            
            # 5. Gestisci eventuali record senza mapping
            orphaned = db.session.execute(text("""
                SELECT DISTINCT leave_type, COUNT(*) as count 
                FROM leave_request 
                WHERE leave_type_id IS NULL 
                GROUP BY leave_type
            """)).fetchall()
            
            if orphaned:
                print("⚠️ Record trovati senza mapping:")
                for row in orphaned:
                    print(f"  • '{row[0]}': {row[1]} record")
                    
                    # Prova a creare una tipologia generica
                    generic_type = LeaveType.query.filter_by(name='Permesso retribuito').first()
                    if generic_type:
                        db.session.execute(text("""
                            UPDATE leave_request 
                            SET leave_type_id = :leave_type_id 
                            WHERE leave_type = :old_type AND leave_type_id IS NULL
                        """), {
                            'leave_type_id': generic_type.id,
                            'old_type': row[0]
                        })
                        print(f"    → Assegnato a 'Permesso retribuito' (ID: {generic_type.id})")
            
            db.session.commit()
            print(f"✅ Migrazione completata! {updated_count} record aggiornati.")
            
            # 6. Verifica finale
            total_requests = db.session.execute(text("SELECT COUNT(*) FROM leave_request")).scalar()
            mapped_requests = db.session.execute(text("SELECT COUNT(*) FROM leave_request WHERE leave_type_id IS NOT NULL")).scalar()
            
            print(f"\nStato finale:")
            print(f"  • Totale richieste: {total_requests}")
            print(f"  • Richieste migrate: {mapped_requests}")
            print(f"  • Richieste non migrate: {total_requests - mapped_requests}")
            
            if total_requests == mapped_requests:
                print("✅ Tutti i record sono stati migrati con successo!")
            else:
                print("⚠️ Alcuni record potrebbero richiedere attenzione manuale.")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ Errore durante la migrazione: {e}")
            raise

if __name__ == '__main__':
    migrate_leave_requests()