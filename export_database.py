#!/usr/bin/env python3
"""
Script per esportare il database Workly in formato SQL
"""
import os
import sys
from datetime import datetime
import logging

# Aggiungi la directory corrente al path
sys.path.insert(0, os.getcwd())

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_database_export():
    """Crea un export completo del database Workly"""
    try:
        from main import app
        import models
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_file = f'workly_database_export_{timestamp}.sql'
        
        with app.app_context():
            with open(export_file, 'w', encoding='utf-8') as f:
                # Header del file
                f.write(f"-- ============================================================================\n")
                f.write(f"-- WORKLY DATABASE EXPORT\n")
                f.write(f"-- Creato il: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"-- Database: Workly Platform\n")
                f.write(f"-- ============================================================================\n\n")
                
                f.write("-- Disable foreign key checks temporaneamente\n")
                f.write("SET session_replication_role = replica;\n\n")
                
                # Export tabelle principali con dati
                tables_to_export = [
                    ('user_roles', models.UserRole),
                    ('users', models.User),
                    ('sedi', models.Sede),
                    ('holidays', models.Holiday),
                    ('aci_tables', models.ACITable),
                    ('attendance_events', models.AttendanceEvent),
                    ('shifts', models.Shift),
                    ('leave_requests', models.LeaveRequest),
                    ('overtime_requests', models.OvertimeRequest), 
                    ('mileage_requests', models.MileageRequest),
                    ('internal_messages', models.InternalMessage),
                    ('expense_reports', models.ExpenseReport),
                    ('expense_categories', models.ExpenseCategory),
                    ('presidio_coverage_templates', models.PresidioCoverageTemplate),
                    ('presidio_coverages', models.PresidioCoverage),
                    ('reperibilita_shifts', models.ReperibilitaShift),
                    ('reperibilita_interventions', models.ReperibilitaIntervention)
                ]
                
                for table_name, model_class in tables_to_export:
                    try:
                        logger.info(f"Esportando tabella: {table_name}")
                        
                        # DELETE per pulire eventuali dati esistenti
                        f.write(f"-- Tabella: {table_name}\n")
                        f.write(f"DELETE FROM {table_name};\n")
                        
                        # Ottieni tutti i record
                        records = model_class.query.all()
                        
                        if records:
                            # Ottieni nomi colonne dalla prima istanza
                            columns = [col.name for col in model_class.__table__.columns]
                            columns_str = ', '.join(columns)
                            
                            f.write(f"INSERT INTO {table_name} ({columns_str}) VALUES\n")
                            
                            values_list = []
                            for record in records:
                                values = []
                                for col in columns:
                                    value = getattr(record, col)
                                    if value is None:
                                        values.append('NULL')
                                    elif isinstance(value, str):
                                        # Escape single quotes
                                        escaped_value = value.replace("'", "''")
                                        values.append(f"'{escaped_value}'")
                                    elif isinstance(value, (datetime)):
                                        values.append(f"'{value.isoformat()}'")
                                    elif isinstance(value, bool):
                                        values.append('TRUE' if value else 'FALSE')
                                    else:
                                        values.append(str(value))
                                
                                values_list.append(f"({', '.join(values)})")
                            
                            # Scrivi tutti i VALUES separati da virgole
                            f.write(',\n'.join(values_list))
                            f.write(';\n\n')
                            
                            logger.info(f"  -> {len(records)} record esportati")
                        else:
                            logger.info(f"  -> Nessun record trovato")
                            f.write(f"-- Nessun dato per {table_name}\n\n")
                            
                    except Exception as e:
                        logger.error(f"Errore esportando {table_name}: {str(e)}")
                        f.write(f"-- ERRORE esportando {table_name}: {str(e)}\n\n")
                
                # Reset sequences per le chiavi primarie auto-increment
                f.write("-- Reset sequences\n")
                for table_name, _ in tables_to_export:
                    f.write(f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), COALESCE(MAX(id), 1)) FROM {table_name};\n")
                
                f.write("\n-- Re-enable foreign key checks\n")
                f.write("SET session_replication_role = DEFAULT;\n\n")
                
                f.write("-- Export completato\n")
        
        logger.info(f"Export completato: {export_file}")
        return export_file
        
    except Exception as e:
        logger.error(f"Errore durante l'export: {str(e)}")
        raise

def create_schema_export():
    """Crea un export solo dello schema (struttura tabelle)"""
    try:
        from main import app
        from models import db
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        schema_file = f'workly_schema_export_{timestamp}.sql'
        
        with app.app_context():
            # Usa SQLAlchemy per generare DDL delle tabelle
            from sqlalchemy.schema import CreateTable
            
            with open(schema_file, 'w', encoding='utf-8') as f:
                f.write(f"-- ============================================================================\n")
                f.write(f"-- WORKLY SCHEMA EXPORT (Solo struttura tabelle)\n") 
                f.write(f"-- Creato il: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"-- ============================================================================\n\n")
                
                for table in db.metadata.tables.values():
                    create_statement = str(CreateTable(table).compile(db.engine))
                    f.write(f"-- Tabella: {table.name}\n")
                    f.write(f"{create_statement};\n\n")
        
        logger.info(f"Schema export completato: {schema_file}")
        return schema_file
        
    except Exception as e:
        logger.error(f"Errore durante l'export schema: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        logger.info("Avvio export database Workly...")
        
        # Export completo (schema + dati)
        full_export = create_database_export()
        
        # Export solo schema
        schema_export = create_schema_export()
        
        print(f"\n✓ Export completati:")
        print(f"  - Database completo: {full_export}")
        print(f"  - Solo schema: {schema_export}")
        print(f"\nPer importare:")
        print(f"  psql -d nome_database -f {full_export}")
        
    except Exception as e:
        logger.error(f"Errore: {str(e)}")
        sys.exit(1)