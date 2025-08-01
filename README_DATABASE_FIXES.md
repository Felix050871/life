# Correzione Incongruenze Database Workly

## Problemi Identificati:

### 1. Campo inconsistente: is_active vs active
**Tabelle con 'is_active' (SBAGLIATE):**
- expense_category
- holiday
- leave_type
- presidio_coverage
- presidio_coverage_template
- reperibilita_coverage

**Tabelle con 'active' (CORRETTE):**
- overtime_type
- sede
- user
- user_role
- work_schedule

### 2. Altri problemi:
- Precision decimal inconsistente in aci_table
- Campi timestamp senza default CURRENT_TIMESTAMP
- Alcuni constraint con nomi inconsistenti

## File generati:

### 1. fix_database_inconsistencies_20250801_110528.sql
Script SQL per correggere database esistente:
- Rinomina is_active → active in 6 tabelle
- Standardizza precision decimal
- Aggiunge default timestamp mancanti

### 2. workly_database_schema_corrected_20250801_110528.sql
Schema database completamente corretto:
- Tutte le tabelle usano campo 'active'
- Precision decimal standardizzata
- Default timestamp aggiunti
- Documentazione aggiornata

## Utilizzo:

### Per correggere database esistente:
```sql
psql -h hostname -U username -d database_name -f fix_database_inconsistencies_20250801_110528.sql
```

### Per creare nuovo database corretto:
```sql
psql -h hostname -U username -d database_name -f workly_database_schema_corrected_20250801_110528.sql
```

## Verifica post-correzione:
Dopo aver applicato le correzioni, tutte le tabelle dovrebbero usare il campo 'active' invece di 'is_active'.

Generato automaticamente il 2025-08-01 11:05:28
