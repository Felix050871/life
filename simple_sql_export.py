#!/usr/bin/env python3
"""
Export SQL semplice e veloce - struttura + dati
"""
import os
from datetime import datetime
from app import app, db
from sqlalchemy import text

def create_sql_dump():
    """Crea dump SQL usando approccio semplice e veloce"""
    with app.app_context():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ns12_workforce_sql_dump_{timestamp}.sql"
        
        print(f"Creando dump SQL: {filename}")
        
        with open(filename, 'w', encoding='utf-8') as f:
            # Header
            f.write("-- NS12 Workforce Management Database Dump\n")
            f.write(f"-- Generated: {datetime.now().isoformat()}\n")
            f.write("-- For PostgreSQL\n\n")
            
            # Get all tables
            tables_result = db.session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """))
            
            tables = [row[0] for row in tables_result]
            print(f"Trovate {len(tables)} tabelle: {', '.join(tables)}")
            
            # DROP statements
            f.write("-- Drop existing tables\n")
            for table in reversed(tables):  # Reverse order for FK constraints
                f.write(f'DROP TABLE IF EXISTS "{table}" CASCADE;\n')
            f.write("\n")
            
            # CREATE TABLE statements  
            f.write("-- Create tables\n")
            for table in tables:
                print(f"Esportando struttura: {table}")
                
                # Get CREATE TABLE statement from PostgreSQL
                create_result = db.session.execute(text(f"""
                    SELECT 
                        'CREATE TABLE "' || table_name || '" (' || chr(10) ||
                        string_agg(
                            '  "' || column_name || '" ' || 
                            CASE 
                                WHEN data_type = 'character varying' THEN 
                                    'VARCHAR' || CASE WHEN character_maximum_length IS NOT NULL 
                                                 THEN '(' || character_maximum_length || ')' 
                                                 ELSE '' END
                                WHEN data_type = 'timestamp without time zone' THEN 'TIMESTAMP'
                                WHEN data_type = 'time without time zone' THEN 'TIME'
                                WHEN data_type = 'boolean' THEN 'BOOLEAN'
                                WHEN data_type = 'date' THEN 'DATE'
                                WHEN data_type = 'integer' THEN 'INTEGER'
                                WHEN data_type = 'text' THEN 'TEXT'
                                WHEN data_type = 'numeric' THEN 'NUMERIC'
                                ELSE UPPER(data_type)
                            END ||
                            CASE WHEN is_nullable = 'NO' THEN ' NOT NULL' ELSE '' END ||
                            CASE WHEN column_default IS NOT NULL THEN ' DEFAULT ' || column_default ELSE '' END,
                            ',' || chr(10)
                            ORDER BY ordinal_position
                        ) || chr(10) || ');'
                    FROM information_schema.columns 
                    WHERE table_name = '{table}' AND table_schema = 'public'
                    GROUP BY table_name
                """))
                
                create_stmt = create_result.scalar()
                if create_stmt:
                    f.write(create_stmt + "\n\n")
            
            # Data export
            f.write("-- Insert data\n")
            for table in tables:
                print(f"Esportando dati: {table}")
                
                # Count records
                count_result = db.session.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                count = count_result.scalar()
                
                f.write(f"-- Table: {table} ({count} records)\n")
                
                if count > 0:
                    # Get column names
                    cols_result = db.session.execute(text(f"""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = '{table}' AND table_schema = 'public'
                        ORDER BY ordinal_position
                    """))
                    columns = [row[0] for row in cols_result]
                    
                    # Export data
                    data_result = db.session.execute(text(f'SELECT * FROM "{table}"'))
                    rows = data_result.fetchall()
                    
                    if rows:
                        col_names = '", "'.join(columns)
                        f.write(f'INSERT INTO "{table}" ("{col_names}") VALUES\n')
                        
                        value_lines = []
                        for row in rows:
                            values = []
                            for value in row:
                                if value is None:
                                    values.append('NULL')
                                elif isinstance(value, str):
                                    escaped = value.replace("'", "''")
                                    values.append(f"'{escaped}'")
                                elif isinstance(value, bool):
                                    values.append('TRUE' if value else 'FALSE')
                                elif isinstance(value, datetime):
                                    values.append(f"'{value.isoformat()}'")
                                else:
                                    values.append(str(value))
                            
                            value_lines.append(f"  ({', '.join(values)})")
                        
                        f.write(',\n'.join(value_lines) + ';\n')
                    
                f.write("\n")
            
            # Footer
            f.write("-- Export completed\n")
            f.write("-- To import: psql -d your_database -f this_file.sql\n")
        
        file_size = os.path.getsize(filename)
        print(f"\n✓ Dump SQL creato: {filename}")
        print(f"  Dimensione: {file_size:,} bytes")
        
        return filename

if __name__ == "__main__":
    try:
        sql_file = create_sql_dump()
        print("\n=== Import Instructions ===")
        print("1. Sul tuo server PostgreSQL:")
        print("   createdb ns12_workforce")
        print(f"2. Importa il dump:")
        print(f"   psql -d ns12_workforce -f {sql_file}")
        print("\n✓ Export SQL completato!")
    except Exception as e:
        print(f"Errore: {e}")
        import traceback
        traceback.print_exc()