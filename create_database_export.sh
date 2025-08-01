#!/bin/bash

# =============================================================================
# SCRIPT PER EXPORT DATABASE WORKLY
# =============================================================================

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
EXPORT_DIR="database_exports"
EXPORT_FILE="workly_database_export_${TIMESTAMP}.sql"
DATA_EXPORT="workly_data_export_${TIMESTAMP}.sql"
SCHEMA_EXPORT="workly_schema_export_${TIMESTAMP}.sql"

echo "=== WORKLY DATABASE EXPORT ==="
echo "Timestamp: $TIMESTAMP"
echo ""

# Crea directory export se non esiste
mkdir -p "$EXPORT_DIR"

# Funzione per esportare tabelle con psql
export_table_data() {
    local table_name=$1
    echo "Esportando tabella: $table_name"
    
    # Crea statement INSERT per la tabella
    psql "$DATABASE_URL" -c "\copy (SELECT * FROM $table_name) TO STDOUT WITH CSV HEADER" > "${EXPORT_DIR}/${table_name}_${TIMESTAMP}.csv" 2>/dev/null
    
    # Conta record
    local count=$(psql "$DATABASE_URL" -tAc "SELECT COUNT(*) FROM $table_name;" 2>/dev/null || echo "0")
    echo "  -> $count record esportati"
}

echo "[INFO] 1. Export struttura database (schema)..."

# Export schema con psql (evita problemi di versione)
cat > "${EXPORT_DIR}/$SCHEMA_EXPORT" << 'EOF'
-- ============================================================================
-- WORKLY DATABASE SCHEMA EXPORT
-- ============================================================================

-- Schema per ricreazione database
EOF

# Ottieni DDL delle tabelle
psql "$DATABASE_URL" -c "
SELECT 'CREATE TABLE ' || tablename || ' (' || 
       string_agg(column_name || ' ' || data_type || 
       CASE WHEN character_maximum_length IS NOT NULL 
            THEN '(' || character_maximum_length || ')' 
            ELSE '' END ||
       CASE WHEN is_nullable = 'NO' THEN ' NOT NULL' ELSE '' END, ', ') || 
       ');' as create_statement
FROM information_schema.tables t
JOIN information_schema.columns c ON t.table_name = c.table_name
WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
GROUP BY t.tablename
ORDER BY t.tablename;
" -t >> "${EXPORT_DIR}/$SCHEMA_EXPORT"

echo "[OK] Schema esportato: ${EXPORT_DIR}/$SCHEMA_EXPORT"

echo ""
echo "[INFO] 2. Export dati tabelle..."

# Lista tabelle del database
TABLES=$(psql "$DATABASE_URL" -tAc "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;")

# Export ogni tabella in CSV
for table in $TABLES; do
    export_table_data "$table"
done

echo ""
echo "[INFO] 3. Creazione script di import SQL..."

# Crea script SQL completo per import
cat > "${EXPORT_DIR}/$EXPORT_FILE" << EOF
-- ============================================================================
-- WORKLY DATABASE COMPLETE EXPORT
-- Creato il: $(date '+%Y-%m-%d %H:%M:%S')
-- ============================================================================

-- Disable foreign key checks
SET session_replication_role = replica;

-- Truncate all tables first
EOF

# Aggiungi TRUNCATE per tutte le tabelle
for table in $TABLES; do
    echo "TRUNCATE TABLE $table CASCADE;" >> "${EXPORT_DIR}/$EXPORT_FILE"
done

echo "" >> "${EXPORT_DIR}/$EXPORT_FILE"

# Per ogni tabella, crea INSERT statements dai CSV
for table in $TABLES; do
    csv_file="${EXPORT_DIR}/${table}_${TIMESTAMP}.csv"
    if [ -f "$csv_file" ] && [ -s "$csv_file" ]; then
        echo "-- Data for table: $table" >> "${EXPORT_DIR}/$EXPORT_FILE"
        
        # Leggi header CSV per nomi colonne
        header=$(head -n1 "$csv_file")
        columns=$(echo "$header" | tr ',' ' ')
        
        # Converti CSV in INSERT statements
        tail -n +2 "$csv_file" | while IFS= read -r line; do
            if [ -n "$line" ]; then
                # Converti CSV line in VALUES format (semplificato)
                values=$(echo "$line" | sed "s/'/\\'/g" | sed "s/,/','/g" | sed "s/^/'/" | sed "s/$/'/" | sed "s/'NULL'/NULL/g")
                echo "INSERT INTO $table ($header) VALUES ($values);" >> "${EXPORT_DIR}/$EXPORT_FILE"
            fi
        done
        echo "" >> "${EXPORT_DIR}/$EXPORT_FILE"
    fi
done

# Footer del file SQL
cat >> "${EXPORT_DIR}/$EXPORT_FILE" << 'EOF'

-- Reset sequences
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r in SELECT schemaname, tablename FROM pg_tables WHERE schemaname = 'public'
    LOOP
        EXECUTE 'SELECT setval(pg_get_serial_sequence(''' || r.schemaname || '.' || r.tablename || ''', ''id''), COALESCE(MAX(id), 1)) FROM ' || r.schemaname || '.' || r.tablename || ';';
    END LOOP;
END $$;

-- Re-enable foreign key checks
SET session_replication_role = DEFAULT;

-- Export completato
EOF

echo "[OK] Export SQL completo: ${EXPORT_DIR}/$EXPORT_FILE"

echo ""
echo "[INFO] 4. Pulizia file temporanei..."
rm -f "${EXPORT_DIR}"/*.csv

echo ""
echo "=== EXPORT COMPLETATO ==="
echo "File creati:"
echo "  • Schema: ${EXPORT_DIR}/$SCHEMA_EXPORT"
echo "  • Dati completi: ${EXPORT_DIR}/$EXPORT_FILE"
echo ""
echo "Per importare in un nuovo database:"
echo "  1. Crea database: createdb nome_nuovo_database"
echo "  2. Importa: psql -d nome_nuovo_database -f ${EXPORT_DIR}/$EXPORT_FILE"
echo ""
echo "File pronti in directory: $EXPORT_DIR/"
ls -la "$EXPORT_DIR"/