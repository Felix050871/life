# 🚀 Workly - Quick Start Guide

## Avvio Rapido (5 minuti)

### 1. Estrazione e Preparazione
```bash
# Estrai il pacchetto
tar -xzf workly_complete_package.tar.gz
cd workly_export

# Copia le configurazioni
cp .env.example .env
```

### 2. Configurazione Minima
Modifica il file `.env`:
```env
# Genera una chiave segreta sicura
FLASK_SECRET_KEY=your-secure-secret-key-here

# Per sviluppo locale (default)
DATABASE_URL=sqlite:///workly.db

# Per produzione PostgreSQL
# DATABASE_URL=postgresql://user:pass@host:port/database
```

### 3. Setup Database e Dipendenze

#### Opzione A: Setup Automatico (CONSIGLIATO)
```bash
# Script tutto-in-uno (crea DB + installa dipendenze + dati esempio)
chmod +x setup_database.sh
./setup_database.sh

# Oppure direttamente con Python:
python create_database.py
```

#### Opzione B: Setup Manuale
```bash
# Crea ambiente virtuale
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oppure: venv\Scripts\activate  # Windows

# Installa dipendenze
pip install -r requirements.txt

# Crea database con dati esempio
python create_database.py
```

#### Opzione C: PostgreSQL (Produzione)
```bash
# Setup PostgreSQL completo
chmod +x setup_postgres.sh
./setup_postgres.sh
```

### 4. Avvio Applicazione
```bash
# Metodo 1: Script automatico (CONSIGLIATO)
python run_local.py

# Metodo 2: Manuale
python main.py

# Metodo 3: Con Flask
flask run --host=0.0.0.0 --port=5000
```

### 5. Primo Accesso
1. Apri il browser su: http://localhost:5000
2. Accedi con le credenziali di default:
   - **Username**: `admin`
   - **Password**: `admin123`
3. ⚠️ **IMPORTANTE**: Cambia immediatamente la password!

## ⚡ Avvio con Docker (Alternativo)

```bash
# Avvia tutti i servizi (Web + Database + Nginx)
docker-compose up -d

# Visualizza i log
docker-compose logs -f

# Ferma i servizi
docker-compose down
```

## 📱 Accesso da Altri Dispositivi

Il server è configurato per accettare connessioni da altri dispositivi nella rete locale:

1. Trova l'IP del tuo computer: `ipconfig` (Windows) o `ifconfig` (Linux/Mac)
2. Accedi da altri dispositivi: `http://TUO_IP:5000`

Esempio: `http://192.168.1.100:5000`

## 🔧 Configurazioni Base

### Utente Amministratore
- Vai in "Gestione Utenti" → Clicca sul tuo profilo
- Modifica nome, cognome, email
- Cambia password nel tab "Sicurezza"

### Prima Configurazione
1. **Sedi di Lavoro**: Crea le sedi della tua organizzazione
2. **Orari di Lavoro**: Configura orari per ogni sede
3. **Utenti**: Aggiungi i membri del team
4. **Ruoli**: Assegna i ruoli appropriati
5. **Permessi**: Personalizza i permessi per ruolo

## 🆘 Risoluzione Problemi Comuni

### ❌ Errore "ModuleNotFoundError"
```bash
# Assicurati che l'ambiente virtuale sia attivo
source venv/bin/activate
pip install -r requirements.txt
```

### ❌ Errore "Database locked" (SQLite)
```bash
# Riavvia l'applicazione
# Se persiste, elimina il file workly.db (perderai i dati)
rm workly.db
```

### ❌ Errore porta già in uso
```bash
# Cambia porta nel file .env
FLASK_PORT=5001

# Oppure trova il processo in uso
lsof -i :5000  # Linux/Mac
netstat -an | findstr :5000  # Windows
```

### ❌ Errore permessi file
```bash
# Linux/Mac: dai permessi alla directory
chmod -R 755 .
chown -R $USER:$USER .
```

## 📚 Prossimi Passi

1. **Leggi la documentazione completa**: `DEPLOYMENT_GUIDE.md`
2. **Esplora le funzionalità**: Dashboard, Presenze, Turni, Reports
3. **Configura il backup**: Importante per i dati aziendali
4. **Personalizza**: Adatta Workly alle tue esigenze

## 🎯 Funzionalità Principali da Testare

- ✅ **Presenze**: Genera il QR code e testa le marcature
- ✅ **Turni**: Crea turni automatici intelligenti  
- ✅ **Permessi**: Richiedi e approva permessi/ferie
- ✅ **Messaggi**: Invia messaggi interni al team
- ✅ **Reports**: Visualizza grafici e esporta dati
- ✅ **Rimborsi**: Gestisci note spese chilometriche

## 💡 Suggerimenti Pro

1. **Performance**: Usa PostgreSQL per >20 utenti
2. **Sicurezza**: Cambia tutte le password di default
3. **Backup**: Configura backup automatici
4. **Monitoraggio**: Controlla regolarmente i log
5. **Updates**: Mantieni aggiornate le dipendenze

---

🎉 **Workly è ora pronto per l'uso!**

Per supporto: consulta `DEPLOYMENT_GUIDE.md` e `CHANGELOG.md`