# 🚀 Setup Workly - Istruzioni Complete

## 1. Estrai i File
```bash
tar -xzf workly-complete.tar.gz
```

## 2. Modifica main.py
Cambia la porta da 5001 a 5000:
```python
from app import app

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)  # Cambia da 5001 a 5000
```

## 3. Inizializza il Database
**IMPORTANTE**: Esegui questo comando per creare il database:
```bash
python setup_database.py
```

Questo script:
- Crea il database SQLite `workly.db`
- Crea tutte le tabelle necessarie
- Inserisce utenti di prova
- Configura sedi e orari di lavoro

## 4. Avvia l'Applicazione
```bash
python main.py
```

## 5. Accedi al Sistema
L'app sarà disponibile su `http://localhost:5000`

### Credenziali di Accesso:
- **Admin**: `admin` / `admin123`
- **Responsabile**: `responsabile` / `resp123`
- **Sviluppatore**: `sviluppatore` / `dev123`
- **Operatore**: `operatore` / `op123`
- **Management**: `management` / `mgmt123`

## 6. Verifica Funzionalità
Dopo il login potrai:
- Gestire sedi aziendali
- Configurare orari di lavoro
- Registrare presenze
- Gestire utenti e ruoli

## Risoluzione Problemi

### Se il database non si crea:
```bash
# Verifica che tutti i file siano presenti
ls -la *.py

# Esegui di nuovo setup
python setup_database.py
```

### Se l'app non si avvia:
```bash
# Verifica dipendenze
pip install -r requirements.txt

# Avvia con debug
python main.py
```