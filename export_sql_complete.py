#!/usr/bin/env python3
"""
Export completo del database in formato SQL per ricreare tutto su un nuovo server
Genera sia la struttura delle tabelle che i dati
"""
import os
from datetime import datetime
from app import app, db
from sqlalchemy import text, inspect

def get_create_table_statements():
    """Genera le istruzioni CREATE TABLE per tutte le tabelle"""
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    
    create_statements = []
    
    # Header del file SQL
    create_statements.append("-- NS12 Workforce Management Database Export")
    create_statements.append(f"-- Generated on: {datetime.now().isoformat()}")
    create_statements.append("-- Database structure and data export")
    create_statements.append("")
    create_statements.append("SET CLIENT_ENCODING TO 'UTF8';")
    create_statements.append("SET STANDARD_CONFORMING_STRINGS TO ON;")
    create_statements.append("")
    
    # DROP tables if exist (in reverse order per foreign keys)
    create_statements.append("-- Drop existing tables")
    tables_reverse = list(reversed(tables))
    for table in tables_reverse:
        create_statements.append(f"DROP TABLE IF EXISTS \"{table}\" CASCADE;")
    create_statements.append("")
    
    # CREATE statements per ogni tabella
    for table_name in tables:
        create_statements.append(f"-- Table: {table_name}")
        
        columns = inspector.get_columns(table_name)
        pk_constraint = inspector.get_pk_constraint(table_name)
        foreign_keys = inspector.get_foreign_keys(table_name)
        indexes = inspector.get_indexes(table_name)
        
        # BUILD CREATE TABLE statement
        col_definitions = []
        
        for col in columns:
            col_def = f'    "{col["name"]}" {get_postgresql_type(col["type"])}'
            
            if col["nullable"] is False:
                col_def += " NOT NULL"
            
            if col["default"] is not None:
                default_val = str(col["default"]).replace("'", "''")
                col_def += f" DEFAULT {default_val}"
                
            col_definitions.append(col_def)
        
        # Primary key
        if pk_constraint and pk_constraint['constrained_columns']:
            pk_cols = '", "'.join(pk_constraint['constrained_columns'])
            col_definitions.append(f'    CONSTRAINT "{table_name}_pkey" PRIMARY KEY ("{pk_cols}")')
        
        create_stmt = f'CREATE TABLE "{table_name}" (\n'
        create_stmt += ',\n'.join(col_definitions)
        create_stmt += '\n);'
        
        create_statements.append(create_stmt)
        create_statements.append("")
        
        # Foreign keys
        for fk in foreign_keys:
            fk_name = fk['name'] or f"{table_name}_{fk['constrained_columns'][0]}_fkey"
            local_cols = '", "'.join(fk['constrained_columns'])
            ref_table = fk['referred_table']
            ref_cols = '", "'.join(fk['referred_columns'])
            
            fk_stmt = f'ALTER TABLE "{table_name}" ADD CONSTRAINT "{fk_name}" '
            fk_stmt += f'FOREIGN KEY ("{local_cols}") REFERENCES "{ref_table}" ("{ref_cols}");'
            create_statements.append(fk_stmt)
        
        if foreign_keys:
            create_statements.append("")
    
    return '\n'.join(create_statements)

def get_postgresql_type(sqlalchemy_type):
    """Converte i tipi SQLAlchemy in tipi PostgreSQL"""
    type_str = str(sqlalchemy_type)
    type_lower = type_str.lower()
    
    if 'integer' in type_lower:
        return 'INTEGER'
    elif 'varchar' in type_lower:
        if '(' in type_str:
            return type_str.upper()
        return 'VARCHAR(255)'
    elif 'text' in type_lower:
        return 'TEXT'
    elif 'boolean' in type_lower:
        return 'BOOLEAN'
    elif 'datetime' in type_lower:
        return 'TIMESTAMP WITHOUT TIME ZONE'
    elif 'date' in type_lower:
        return 'DATE'
    elif 'time' in type_lower:
        return 'TIME WITHOUT TIME ZONE'
    elif 'numeric' in type_lower or 'decimal' in type_lower:
        return 'NUMERIC'
    elif 'float' in type_lower:
        return 'DOUBLE PRECISION'
    else:
        return 'TEXT'  # Fallback sicuro

def get_insert_statements():
    """Genera le istruzioni INSERT per tutti i dati"""
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    
    insert_statements = []
    insert_statements.append("-- Data export")
    insert_statements.append("")
    
    for table_name in tables:
        insert_statements.append(f"-- Data for table: {table_name}")
        
        # Query per ottenere tutti i dati
        try:
            result = db.session.execute(text(f'SELECT * FROM "{table_name}"'))
            rows = result.fetchall()
            
            if rows:
                # Ottieni i nomi delle colonne
                columns = [col.name for col in result.keys()]
                col_names = '", "'.join(columns)
                
                insert_statements.append(f'INSERT INTO "{table_name}" ("{col_names}") VALUES')
                
                value_sets = []
                for row in rows:
                    values = []
                    for i, value in enumerate(row):
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
                    
                    value_sets.append(f"    ({', '.join(values)})")
                
                insert_statements.append(',\n'.join(value_sets) + ';')
                insert_statements.append("")
                
                print(f"✓ Esportati {len(rows)} record da tabella {table_name}")
            else:
                insert_statements.append(f"-- No data in table {table_name}")
                insert_statements.append("")
                print(f"  Tabella {table_name} vuota")
                
        except Exception as e:
            print(f"✗ Errore esportando tabella {table_name}: {e}")
            insert_statements.append(f"-- Error exporting table {table_name}: {e}")
            insert_statements.append("")
    
    return '\n'.join(insert_statements)

def generate_complete_sql_dump():
    """Genera un dump SQL completo con struttura e dati"""
    with app.app_context():
        print("=== Export SQL Completo NS12 Workforce Management ===")
        print("")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ns12_workforce_complete_dump_{timestamp}.sql"
        
        print("Generando struttura database...")
        structure_sql = get_create_table_statements()
        
        print("Esportando dati...")
        data_sql = get_insert_statements()
        
        # Combina struttura e dati
        complete_sql = structure_sql + "\n\n" + data_sql
        
        # Aggiungi footer
        complete_sql += "\n-- Export completed successfully\n"
        complete_sql += "-- To import: psql -d database_name -f this_file.sql\n"
        
        # Salva file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(complete_sql)
        
        print(f"\n✓ Export SQL completo generato: {filename}")
        print(f"  Dimensione: {os.path.getsize(filename)} bytes")
        print("")
        print("Per importare su un nuovo server:")
        print(f"  1. Crea database vuoto: createdb ns12_workforce")
        print(f"  2. Importa dump: psql -d ns12_workforce -f {filename}")
        print("")
        
        return filename

if __name__ == "__main__":
    try:
        sql_file = generate_complete_sql_dump()
        print("=== Export SQL completato con successo! ===")
    except Exception as e:
        print(f"Errore durante export: {e}")
        import traceback
        traceback.print_exc()