#!/bin/bash

# =============================================================================
# WORKLY - SCRIPT DI INSTALLAZIONE LOCALE PER SISTEMI UNIX/LINUX/MACOS
# Sistema di Gestione Workforce con PostgreSQL
# =============================================================================

set -e  # Exit on any error

echo "==================================================================================="
echo "                    WORKLY - INSTALLAZIONE LOCALE POSTGRESQL"
echo "==================================================================================="
echo ""

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funzioni di utilità
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Verifica che lo script sia eseguito dalla directory corretta
if [ ! -f "main.py" ] || [ ! -f "models.py" ]; then
    print_error "Errore: Esegui lo script dalla directory principale del progetto Workly"
    print_error "Assicurati che i file main.py e models.py siano presenti"
    exit 1
fi

print_info "Directory corrente: $(pwd)"
print_info "Avvio installazione Workly con PostgreSQL..."
echo ""

# =============================================================================
# CONTROLLI PREREQUISITI
# =============================================================================

print_info "1. Verifica prerequisiti sistema..."

# Controlla Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    print_success "Python3 trovato: versione $PYTHON_VERSION"
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
    if [[ $PYTHON_VERSION == 3.* ]]; then
        print_success "Python trovato: versione $PYTHON_VERSION"
        PYTHON_CMD="python"
    else
        print_error "Richiesta Python 3.7+, trovata versione: $PYTHON_VERSION"
        exit 1
    fi
else
    print_error "Python 3.7+ non trovato. Installa Python 3.7 o superiore."
    exit 1
fi

# Controlla pip
if command -v pip3 &> /dev/null; then
    print_success "pip3 trovato"
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    print_success "pip trovato"
    PIP_CMD="pip"
else
    print_error "pip non trovato. Installa pip per Python 3."
    exit 1
fi

# Controlla PostgreSQL
if command -v psql &> /dev/null; then
    PG_VERSION=$(psql --version | awk '{print $3}')
    print_success "PostgreSQL trovato: versione $PG_VERSION"
else
    print_error "PostgreSQL non trovato."
    print_error "Installa PostgreSQL prima di continuare:"
    print_error "  Ubuntu/Debian: sudo apt install postgresql postgresql-contrib"
    print_error "  CentOS/RHEL: sudo yum install postgresql postgresql-server postgresql-contrib"
    print_error "  macOS: brew install postgresql"
    exit 1
fi

echo ""

# =============================================================================
# CONFIGURAZIONE AMBIENTE VIRTUALE
# =============================================================================

print_info "2. Configurazione ambiente virtuale..."

VENV_DIR="./workly_venv"

if [ -d "$VENV_DIR" ]; then
    print_warning "Ambiente virtuale esistente trovato, lo rimuovo..."
    rm -rf "$VENV_DIR"
fi

print_info "Creazione nuovo ambiente virtuale in: $VENV_DIR"
$PYTHON_CMD -m venv "$VENV_DIR"

# Attiva ambiente virtuale
source "$VENV_DIR/bin/activate"
print_success "Ambiente virtuale attivato"

# Aggiorna pip nell'ambiente virtuale
print_info "Aggiornamento pip nell'ambiente virtuale..."
$VENV_DIR/bin/pip install --upgrade pip
print_success "pip aggiornato"

echo ""

# =============================================================================
# INSTALLAZIONE DIPENDENZE
# =============================================================================

print_info "3. Installazione dipendenze Python..."

if [ -f "requirements.txt" ]; then
    print_info "Installazione da requirements.txt..."
    $VENV_DIR/bin/pip install -r requirements.txt
    print_success "Dipendenze installate da requirements.txt"
else
    print_info "requirements.txt non trovato, installazione dipendenze base..."
    
    # Dipendenze principali per PostgreSQL
    DEPS=(
        "Flask>=2.3.0"
        "Flask-Login>=0.6.0"
        "Flask-SQLAlchemy>=3.0.0"
        "Flask-WTF>=1.1.0"
        "WTForms>=3.0.0"
        "SQLAlchemy>=2.0.0"
        "psycopg2-binary>=2.9.0"
        "Werkzeug>=2.3.0"
        "gunicorn>=20.1.0"
        "python-dotenv>=1.0.0"
        "Pillow>=9.0.0"
        "openpyxl>=3.1.0"
        "qrcode[pil]>=7.4.0"
        "reportlab>=4.0.0"
        "defusedcsv>=2.0.0"
        "email-validator>=2.0.0"
        "PyJWT>=2.6.0"
    )
    
    for dep in "${DEPS[@]}"; do
        print_info "Installazione: $dep"
        $VENV_DIR/bin/pip install "$dep"
    done
    
    print_success "Dipendenze base installate"
fi

echo ""

# =============================================================================
# CONFIGURAZIONE DATABASE POSTGRESQL
# =============================================================================

print_info "4. Configurazione database PostgreSQL..."

# Chiede credenziali PostgreSQL
echo ""
print_info "Inserisci le credenziali PostgreSQL:"
read -p "Host PostgreSQL (default: localhost): " PG_HOST
PG_HOST=${PG_HOST:-localhost}

read -p "Porta PostgreSQL (default: 5432): " PG_PORT
PG_PORT=${PG_PORT:-5432}

read -p "Nome database (default: workly_db): " PG_DATABASE
PG_DATABASE=${PG_DATABASE:-workly_db}

read -p "Username PostgreSQL (default: postgres): " PG_USER
PG_USER=${PG_USER:-postgres}

read -s -p "Password PostgreSQL: " PG_PASSWORD
echo ""

# Test connessione PostgreSQL
print_info "Test connessione PostgreSQL..."
export PGPASSWORD="$PG_PASSWORD"

if psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d postgres -c "\q" 2>/dev/null; then
    print_success "Connessione PostgreSQL riuscita"
else
    print_error "Impossibile connettersi a PostgreSQL con le credenziali fornite"
    print_error "Verifica host, porta, username e password"
    exit 1
fi

# Crea database se non esiste
print_info "Creazione database '$PG_DATABASE'..."
if psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d postgres -lqt | cut -d \| -f 1 | grep -qw "$PG_DATABASE"; then
    print_warning "Database '$PG_DATABASE' già esistente"
    read -p "Vuoi ricreare il database? (y/N): " RECREATE_DB
    if [[ $RECREATE_DB =~ ^[Yy]$ ]]; then
        psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d postgres -c "DROP DATABASE IF EXISTS $PG_DATABASE;"
        psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d postgres -c "CREATE DATABASE $PG_DATABASE;"
        print_success "Database ricreato"
    else
        print_info "Utilizzo database esistente"
    fi
else
    psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d postgres -c "CREATE DATABASE $PG_DATABASE;"
    print_success "Database '$PG_DATABASE' creato"
fi

echo ""

# =============================================================================
# CREAZIONE FILE DI CONFIGURAZIONE
# =============================================================================

print_info "5. Creazione file di configurazione..."

# Crea directory config se non esiste
CONFIG_DIR="./config"
mkdir -p "$CONFIG_DIR"

# Genera chiave segreta sicura
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Crea file .env
ENV_FILE="./.env"
cat > "$ENV_FILE" << EOF
# =============================================================================
# WORKLY - CONFIGURAZIONE AMBIENTE LOCALE POSTGRESQL
# =============================================================================

# Database PostgreSQL
DATABASE_URL=postgresql://$PG_USER:$PG_PASSWORD@$PG_HOST:$PG_PORT/$PG_DATABASE
PGHOST=$PG_HOST
PGPORT=$PG_PORT
PGDATABASE=$PG_DATABASE
PGUSER=$PG_USER
PGPASSWORD=$PG_PASSWORD

# Flask Configuration
FLASK_SECRET_KEY=$SECRET_KEY
SESSION_SECRET=$SECRET_KEY
FLASK_ENV=production
FLASK_DEBUG=False

# Workly Configuration
WORKLY_ADMIN_EMAIL=admin@workly.local
WORKLY_COMPANY_NAME=Workly Platform
WORKLY_TIMEZONE=Europe/Rome

# Server Configuration
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
WORKERS=4
EOF

print_success "File .env creato: $ENV_FILE"

# Crea script di avvio locale
STARTUP_SCRIPT="./start_workly.sh"
cat > "$STARTUP_SCRIPT" << 'EOF'
#!/bin/bash

# =============================================================================
# WORKLY - SCRIPT DI AVVIO LOCALE
# =============================================================================

set -e

# Colori per output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Verifica directory
if [ ! -f "main.py" ]; then
    print_error "Esegui lo script dalla directory principale del progetto Workly"
    exit 1
fi

# Attiva ambiente virtuale
VENV_DIR="./workly_venv"
if [ ! -d "$VENV_DIR" ]; then
    print_error "Ambiente virtuale non trovato. Esegui prima install_local.sh"
    exit 1
fi

source "$VENV_DIR/bin/activate"
print_info "Ambiente virtuale attivato"

# Carica variabili ambiente
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
    print_success "Configurazione caricata da .env"
else
    print_error "File .env non trovato"
    exit 1
fi

# Inizializza database se necessario
print_info "Inizializzazione database..."
python3 -c "
from main import app
with app.app_context():
    from models import db
    db.create_all()
    print('✓ Database inizializzato')
"

# Avvia server
print_info "Avvio Workly su http://${FLASK_HOST:-127.0.0.1}:${FLASK_PORT:-5000}"
print_info "Premi Ctrl+C per terminare"
echo ""

exec gunicorn --bind "${FLASK_HOST:-127.0.0.1}:${FLASK_PORT:-5000}" --workers "${WORKERS:-4}" --timeout 120 --access-logfile - --error-logfile - main:app
EOF

chmod +x "$STARTUP_SCRIPT"
print_success "Script di avvio creato: $STARTUP_SCRIPT"

echo ""

# =============================================================================
# INIZIALIZZAZIONE DATABASE
# =============================================================================

print_info "6. Inizializzazione database..."

# Imposta variabili ambiente per Flask
export DATABASE_URL="postgresql://$PG_USER:$PG_PASSWORD@$PG_HOST:$PG_PORT/$PG_DATABASE"
export FLASK_SECRET_KEY="$SECRET_KEY"
export SESSION_SECRET="$SECRET_KEY"

print_info "Creazione tabelle database..."

# Inizializza database usando l'ambiente virtuale Python
$VENV_DIR/bin/python3 -c "
import sys
import os

# Aggiungi la directory corrente al path
sys.path.insert(0, os.getcwd())

try:
    from main import app
    with app.app_context():
        from models import db
        
        # Crea tutte le tabelle
        db.create_all()
        print('✓ Tabelle database create con successo')
        
        # Verifica connessione
        result = db.session.execute(db.text('SELECT 1')).scalar()
        if result == 1:
            print('✓ Connessione database verificata')
        else:
            print('✗ Errore verifica connessione database')
            sys.exit(1)
            
except Exception as e:
    print(f'✗ Errore inizializzazione database: {str(e)}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    print_success "Database inizializzato correttamente"
else
    print_error "Errore durante l'inizializzazione del database"
    exit 1
fi

echo ""

# =============================================================================
# CREAZIONE UTENTE AMMINISTRATORE
# =============================================================================

print_info "7. Creazione utente amministratore..."

echo ""
print_info "Inserisci i dati per l'utente amministratore:"
read -p "Nome: " ADMIN_FIRST_NAME
read -p "Cognome: " ADMIN_LAST_NAME
read -p "Email: " ADMIN_EMAIL
read -p "Username: " ADMIN_USERNAME
read -s -p "Password: " ADMIN_PASSWORD
echo ""

# Crea utente admin
$VENV_DIR/bin/python3 -c "
import sys
import os

# Aggiungi la directory corrente al path
sys.path.insert(0, os.getcwd())

try:
    from main import app
    with app.app_context():
        from models import db, User, UserRole
        from werkzeug.security import generate_password_hash
        
        # Verifica se l'utente esiste già
        existing_user = User.query.filter_by(username='$ADMIN_USERNAME').first()
        if existing_user:
            print('✗ Utente con username \"$ADMIN_USERNAME\" già esistente')
            sys.exit(1)
        
        existing_email = User.query.filter_by(email='$ADMIN_EMAIL').first()
        if existing_email:
            print('✗ Utente con email \"$ADMIN_EMAIL\" già esistente')
            sys.exit(1)
        
        # Trova o crea ruolo amministratore
        admin_role = UserRole.query.filter_by(name='Amministratore').first()
        if not admin_role:
            # Crea ruolo amministratore con tutti i permessi
            admin_role = UserRole(
                name='Amministratore',
                description='Amministratore sistema con accesso completo',
                can_manage_users=True,
                can_view_all_users=True,
                can_edit_all_users=True,
                can_delete_users=True,
                can_manage_roles=True,
                can_view_attendance=True,
                can_edit_attendance=True,
                can_manage_shifts=True,
                can_view_all_shifts=True,
                can_create_shifts=True,
                can_edit_shifts=True,
                can_delete_shifts=True,
                can_manage_holidays=True,
                can_view_reports=True,
                can_export_data=True,
                can_manage_sedi=True,
                can_view_dashboard=True,
                can_manage_leave_requests=True,
                can_approve_leave_requests=True,
                can_view_leave_requests=True,
                can_create_leave_requests=True,
                can_manage_overtime_requests=True,
                can_approve_overtime_requests=True,
                can_view_overtime_requests=True,
                can_create_overtime_requests=True,
                can_manage_mileage_requests=True,
                can_approve_mileage_requests=True,
                can_view_mileage_requests=True,
                can_create_mileage_requests=True,
                can_manage_internal_messages=True,
                can_send_internal_messages=True,
                can_view_internal_messages=True,
                can_manage_aci_tables=True,
                can_view_aci_tables=True
            )
            db.session.add(admin_role)
            db.session.flush()
        
        # Crea utente amministratore
        admin_user = User(
            first_name='$ADMIN_FIRST_NAME',
            last_name='$ADMIN_LAST_NAME',
            email='$ADMIN_EMAIL',
            username='$ADMIN_USERNAME',
            password_hash=generate_password_hash('$ADMIN_PASSWORD'),
            is_active=True,
            all_sedi=True,
            role_id=admin_role.id
        )
        
        db.session.add(admin_user)
        db.session.commit()
        
        print('✓ Utente amministratore creato con successo')
        print(f'  Username: $ADMIN_USERNAME')
        print(f'  Email: $ADMIN_EMAIL')
        print(f'  Ruolo: {admin_role.name}')
        
except Exception as e:
    print(f'✗ Errore creazione utente amministratore: {str(e)}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    print_success "Utente amministratore creato"
else
    print_error "Errore durante la creazione dell'utente amministratore"
    exit 1
fi

echo ""

# =============================================================================
# DATI DI TEST (OPZIONALE)
# =============================================================================

print_info "8. Dati di test (opzionale)..."

read -p "Vuoi caricare dati di test nel database? (y/N): " LOAD_TEST_DATA
if [[ "$LOAD_TEST_DATA" =~ ^[Yy]$ ]]; then
    print_info "Caricamento dati di test..."
    if [ -f "populate_test_data.py" ]; then
        $VENV_DIR/bin/python3 populate_test_data.py
        if [ $? -eq 0 ]; then
            print_success "Dati di test caricati con successo"
        else
            print_warning "Errore durante il caricamento dati di test"
        fi
    else
        print_warning "File populate_test_data.py non trovato"
    fi
else
    print_info "Dati di test saltati"
fi

echo ""

# =============================================================================
# COMPLETAMENTO INSTALLAZIONE
# =============================================================================

print_success "==================================================================================="
print_success "                    INSTALLAZIONE WORKLY COMPLETATA CON SUCCESSO!"
print_success "==================================================================================="
echo ""

print_info "Configurazione:"
print_info "  • Database PostgreSQL: $PG_HOST:$PG_PORT/$PG_DATABASE"
print_info "  • Ambiente virtuale: $VENV_DIR"
print_info "  • Configurazione: .env"
print_info "  • Utente admin: $ADMIN_USERNAME ($ADMIN_EMAIL)"
echo ""

print_info "Per avviare Workly:"
print_success "  ./start_workly.sh"
echo ""

print_info "Per accedere a Workly:"
print_success "  http://127.0.0.1:5000"
print_success "  Username: $ADMIN_USERNAME"
print_success "  Password: [quella inserita]"
echo ""

print_warning "Note importanti:"
print_warning "  • Mantieni sicuro il file .env (contiene credenziali database)"
print_warning "  • Per aggiornamenti, mantieni il database e ricrea solo l'ambiente virtuale"
print_warning "  • Per backup: esporta il database PostgreSQL con pg_dump"
echo ""

print_success "Workly è pronto per l'uso!"