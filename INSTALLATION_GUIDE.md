# Workly - Guida all'Installazione

## Indice
1. [Requisiti di Sistema](#requisiti-di-sistema)
2. [Installazione Locale](#installazione-locale)
3. [Installazione su Server](#installazione-su-server)
4. [Deployment su Replit](#deployment-su-replit)
5. [Configurazione Database](#configurazione-database)
6. [Variabili d'Ambiente](#variabili-dambiente)
7. [Prima Configurazione](#prima-configurazione)
8. [Troubleshooting](#troubleshooting)

## Requisiti di Sistema

### Minimi
- **Python**: 3.11 o superiore
- **RAM**: 512MB
- **Storage**: 1GB liberi
- **Database**: PostgreSQL 13+ (produzione) o SQLite (sviluppo)

### Raccomandati
- **Python**: 3.11+
- **RAM**: 1GB+
- **Storage**: 2GB+
- **Database**: PostgreSQL 15+
- **OS**: Ubuntu 20.04+, CentOS 8+, Windows 10+

## Installazione Locale

### 1. Clone del Repository
```bash
git clone <repository-url>
cd workly
```

### 2. Ambiente Virtuale Python
```bash
# Creazione ambiente virtuale
python -m venv venv

# Attivazione (Linux/Mac)
source venv/bin/activate

# Attivazione (Windows)
venv\Scripts\activate
```

### 3. Installazione Dipendenze
```bash
pip install -r requirements.txt
```

### 4. Configurazione Database Locale (SQLite)
```bash
# Crea il database SQLite automaticamente
export DATABASE_URL="sqlite:///workly.db"
export FLASK_SECRET_KEY="your-secret-key-here"
```

### 5. Avvio Applicazione
```bash
# Modalità sviluppo
python main.py

# Con Gunicorn (raccomandato)
gunicorn --bind 0.0.0.0:5000 --reload main:app
```

### 6. Accesso
- URL: http://localhost:5000
- Login: admin / password123

## Installazione su Server

### 1. Preparazione Server (Ubuntu/Debian)
```bash
# Aggiornamento sistema
sudo apt update && sudo apt upgrade -y

# Installazione dipendenze sistema
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib nginx
```

### 2. Configurazione PostgreSQL
```bash
# Accesso PostgreSQL
sudo -u postgres psql

# Creazione database e utente
CREATE DATABASE workly;
CREATE USER workly_user WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE workly TO workly_user;
\q
```

### 3. Setup Applicazione
```bash
# Creazione utente applicazione
sudo useradd -m -s /bin/bash workly
sudo su - workly

# Clone e setup
git clone <repository-url> /home/workly/app
cd /home/workly/app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Configurazione Variabili d'Ambiente
```bash
# Crea file .env
cat > /home/workly/app/.env << EOF
DATABASE_URL=postgresql://workly_user:secure_password@localhost/workly
FLASK_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
FLASK_ENV=production
PORT=5000
EOF
```

### 5. Service Systemd
```bash
# Crea service file
sudo cat > /etc/systemd/system/workly.service << EOF
[Unit]
Description=Workly Workforce Management
After=network.target

[Service]
Type=exec
User=workly
Group=workly
WorkingDirectory=/home/workly/app
Environment=PATH=/home/workly/app/venv/bin
EnvironmentFile=/home/workly/app/.env
ExecStart=/home/workly/app/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 main:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Abilitazione e avvio
sudo systemctl daemon-reload
sudo systemctl enable workly
sudo systemctl start workly
```

### 6. Configurazione Nginx
```bash
# Configurazione Nginx
sudo cat > /etc/nginx/sites-available/workly << EOF
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Static files
    location /static {
        alias /home/workly/app/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Abilitazione sito
sudo ln -s /etc/nginx/sites-available/workly /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 7. SSL con Let's Encrypt
```bash
# Installazione Certbot
sudo apt install -y certbot python3-certbot-nginx

# Ottenimento certificato
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Aggiungi: 0 12 * * * /usr/bin/certbot renew --quiet
```

## Deployment su Replit

### 1. Configurazione Replit
Il progetto è già configurato per Replit con:
- `replit.nix`: Configurazione ambiente Nix
- `.replit`: Configurazione run command
- `pyproject.toml`: Gestione dipendenze Python

### 2. Variabili d'Ambiente Replit
Nel pannello Secrets di Replit, configura:
```
DATABASE_URL=<replit-postgresql-url>
FLASK_SECRET_KEY=<generated-secret-key>
```

### 3. Database Replit
Replit fornisce automaticamente PostgreSQL. Il `DATABASE_URL` è disponibile nell'ambiente.

### 4. Deploy Automatico
```bash
# Il sistema è configurato per auto-deploy
# Comando run: gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

## Configurazione Database

### Inizializzazione Schema
```python
# Il database viene inizializzato automaticamente al primo avvio
# Schema creato tramite SQLAlchemy models

# Per ripopolare dati di test:
python populate_test_data.py
```

### Backup Database
```bash
# PostgreSQL backup
pg_dump -U workly_user -h localhost workly > backup_$(date +%Y%m%d).sql

# Restore
psql -U workly_user -h localhost -d workly < backup_file.sql
```

## Variabili d'Ambiente

### Obbligatorie
```bash
DATABASE_URL=postgresql://user:pass@host:port/dbname
FLASK_SECRET_KEY=your-very-secure-secret-key
```

### Opzionali
```bash
FLASK_ENV=production                    # development/production
PORT=5000                              # Porta applicazione
DEBUG=False                            # True per debug mode
LOG_LEVEL=INFO                         # DEBUG/INFO/WARNING/ERROR
```

### Generazione Secret Key
```python
import secrets
print(secrets.token_hex(32))
```

## Prima Configurazione

### 1. Accesso Iniziale
- URL: http://your-domain.com
- Username: `admin`
- Password: `password123`

### 2. Configurazione Base
1. **Cambio password admin**: Dashboard → Profilo
2. **Creazione sedi**: Menu Sedi → Aggiungi
3. **Configurazione orari**: Menu Orari → Nuovo
4. **Creazione ruoli**: Menu Ruoli → Personalizza permessi
5. **Aggiunta utenti**: Menu Utenti → Crea nuovo

### 3. Personalizzazione
1. **Tipologie ferie**: Gestione → Tipologie Permessi
2. **Categorie spese**: Note Spese → Gestisci Categorie
3. **Festività**: Menu Festività → Configura calendario
4. **QR Codes**: Gestione QR → Rigenera se necessario

### 4. Test Funzionalità
1. **Registrazione presenze**: Dashboard → Entrata/Uscita
2. **Richiesta permessi**: Ferie/Permessi → Nuova richiesta
3. **Nota spese**: Note Spese → Crea nuova
4. **Export dati**: Qualsiasi sezione → Export Excel

## Troubleshooting

### Errori Comuni

#### 1. Database Connection Error
```
sqlalchemy.exc.OperationalError: could not connect to server
```
**Soluzione**: Verifica DATABASE_URL e che PostgreSQL sia attivo
```bash
sudo systemctl status postgresql
sudo systemctl start postgresql
```

#### 2. CSRF Token Missing
```
400 Bad Request: The CSRF session token is missing
```
**Soluzione**: Verifica FLASK_SECRET_KEY sia configurato
```bash
export FLASK_SECRET_KEY="your-secret-key"
```

#### 3. Permission Denied
```
PermissionError: [Errno 13] Permission denied
```
**Soluzione**: Verifica permessi file e cartelle
```bash
sudo chown -R workly:workly /home/workly/app
chmod +x /home/workly/app/main.py
```

#### 4. Import Error
```
ImportError: No module named 'flask'
```
**Soluzione**: Attiva virtual environment e installa dipendenze
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Log File Locations
- **Applicazione**: `journalctl -u workly -f`
- **Nginx**: `/var/log/nginx/error.log`
- **PostgreSQL**: `/var/log/postgresql/postgresql-*.log`

### Performance Tuning

#### 1. PostgreSQL Optimization
```sql
-- postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
```

#### 2. Gunicorn Workers
```bash
# Formula: (2 x CPU cores) + 1
gunicorn --workers 5 --bind 0.0.0.0:5000 main:app
```

#### 3. Nginx Caching
```nginx
location /static {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### Monitoring

#### 1. Health Check
```bash
curl -f http://localhost:5000/health || echo "App down"
```

#### 2. Database Monitor
```sql
SELECT * FROM pg_stat_activity WHERE state = 'active';
```

#### 3. Log Monitoring
```bash
tail -f /var/log/workly/app.log | grep ERROR
```

## Supporto

Per problemi di installazione:
1. Verifica i log dell'applicazione
2. Controlla la configurazione delle variabili d'ambiente
3. Verifica connessione database
4. Consulta la documentazione ufficiale Flask/PostgreSQL