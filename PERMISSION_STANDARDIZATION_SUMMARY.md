# Riepilogo Standardizzazione Sistema Permessi

## Data: 7 Agosto 2025

## Problema Identificato
Il sistema dei permessi presentava inconsistenze nella gestione della distinzione tra dati "miei" vs "tutti":

- **Alcuni moduli** usavano logica codificata (es. Reperibilità, Presenze, Ferie/Permessi)
- **Altri moduli** avevano permessi espliciti (es. Note Spese, Straordinari, Rimborsi km)

## Soluzione Implementata

### 1. Permessi Standardizzati Aggiunti

| Modulo | Permesso Generale | Nuovo Permesso Personale |
|--------|------------------|--------------------------|
| Reperibilità | `can_view_reperibilità` | `can_view_my_reperibilità` |
| Presenze | `can_view_attendance` | `can_view_my_attendance` |
| Ferie/Permessi | `can_view_leave` | `can_view_my_leave` |

### 2. Permessi Esistenti Riorganizzati

| Modulo | Prima | Dopo |
|--------|-------|------|
| Note Spese | `can_view_expense_reports` | `can_view_expense_reports` (tutte) + `can_view_my_expense_reports` (mie) |
| Straordinari | `can_view_overtime_requests` | `can_view_overtime_requests` (tutte) + `can_view_my_overtime_requests` (mie) |
| Rimborsi km | `can_view_mileage_requests` | `can_view_mileage_requests` (tutte) + `can_view_my_mileage_requests` (mie) |

### 3. Logica Applicata

- **PERMESSO GENERALE (`can_view_*`)** = Può vedere TUTTI i dati (con eventuale filtro per sede)
- **PERMESSO PERSONALE (`can_view_my_*`)** = Può vedere SOLO i propri dati
- **Se ha il permesso generale**, automaticamente gli è stato assegnato anche quello personale durante l'aggiornamento

### 4. Aggiornamenti Database

✅ **Tutti i ruoli aggiornati automaticamente:**
- **Supervisore**: Aggiunto `can_view_my_attendance` = true (aveva `can_view_attendance`)
- **Responsabile**: Aggiunti tutti e 3 i nuovi permessi = true (aveva i permessi generali)
- **Operatore**: Aggiunti tutti e 3 i nuovi permessi = true (aveva i permessi generali)
- **Amministratore**: Aggiunti tutti i nuovi permessi = false (non aveva permessi generali)

### 5. Codice Aggiornato

✅ **Modello User (models.py):**
- Aggiunti metodi `can_view_my_reperibilità()`, `can_view_my_attendance()`, `can_view_my_leave()`
- Aggiornato `can_access_reperibilità_menu()` per includere il nuovo permesso

✅ **Route Dashboard (routes.py):**
- Widget Note Spese ora usa logica permessi esplicita invece di controlli nel codice
- Pagina Note Spese aggiornata per usare nuova logica

### 6. Vantaggi della Standardizzazione

1. **Chiarezza**: Non più logica mista codice/permessi - tutto esplicito nei permessi
2. **Consistenza**: Stesso pattern per tutti i moduli
3. **Flessibilità**: Possibili configurazioni:
   - Solo dati personali (`can_view_my_*` = true, `can_view_*` = false)
   - Solo dati di tutti (`can_view_*` = true, `can_view_my_*` = false)
   - Entrambi (`can_view_*` = true, `can_view_my_*` = true)
4. **Manutenibilità**: Logica centralizzata nei permessi, non sparsa nel codice

## Stato Attuale

✅ **COMPLETATO**
- [x] Aggiornamento definizioni permessi in models.py
- [x] Aggiunta nuovi metodi nel modello User
- [x] Aggiornamento automatico di tutti i ruoli esistenti nel database
- [x] Correzione logica nel dashboard widget note spese
- [x] Correzione logica nella pagina note spese

🔄 **DA COMPLETARE**
- [ ] Aggiornare le altre pagine per usare la nuova logica (Reperibilità, Presenze, Ferie/Permessi)
- [ ] Testare tutti i permessi con ogni ruolo
- [ ] Documentare la nuova logica per gli amministratori di sistema

## Note Tecniche

- Lo script `update_permission_system.py` può essere riutilizzato per futuri aggiornamenti di massa
- I permessi esistenti non sono stati modificati per compatibilità
- La transizione è stata completamente retrocompatibile