#!/bin/bash
set -e

# Workly Platform - Script Installazione Automatica Linux/macOS
# Versione: 1.0
# Data: 31 Luglio 2025

echo "=========================================="
echo "   WORKLY PLATFORM INSTALLER v1.0"
echo "=========================================="
echo ""

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funzioni helper
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Controllo sistema operativo
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/debian_version ]; then
            OS="debian"
            PACKAGE_MANAGER="apt"
        elif [ -f /etc/redhat-release ]; then
            OS="redhat"
            PACKAGE_MANAGER="yum"
        else
            OS="linux"
            PACKAGE_MANAGER="unknown"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        PACKAGE_MANAGER="brew"
    else
        OS="unknown"
        PACKAGE_MANAGER="unknown"
    fi
    
    print_info "Sistema operativo rilevato: $OS"
}

# Controllo permessi
check_permissions() {
    if [[ $EUID -eq 0 ]]; then
        print_warning "Attenzione: stai eseguendo come root. Alcuni passi potrebbero non funzionare correttamente."
        read -p "Vuoi continuare? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Controllo dipendenze sistema
check_system_deps() {
    print_info "Controllo dipendenze di sistema..."
    
    # Controllo Git
    if ! command -v git &> /dev/null; then
        print_error "Git non è installato. Installazione in corso..."
        case $PACKAGE_MANAGER in
            "apt")
                sudo apt update && sudo apt install -y git
                ;;
            "yum")
                sudo yum install -y git
                ;;
            "brew")
                brew install git
                ;;
            *)
                print_error "Installa Git manualmente e riprova"
                exit 1
                ;;
        esac
    fi
    print_success "Git disponibile"
    
    # Controllo curl/wget
    if ! command -v curl &> /dev/null && ! command -v wget &> /dev/null; then
        print_error "curl o wget necessari. Installazione curl..."
        case $PACKAGE_MANAGER in
            "apt")
                sudo apt install -y curl
                ;;
            "yum")
                sudo yum install -y curl
                ;;
            "brew")
                brew install curl
                ;;
        esac
    fi
    print_success "Download tools disponibili"
}

# Installazione Python
install_python() {
    print_info "Controllo installazione Python..."
    
    # Controllo se Python 3.9+ è disponibile
    PYTHON_CMD=""
    for cmd in python3.11 python3.10 python3.9 python3 python; do
        if command -v $cmd &> /dev/null; then
            VERSION=$($cmd --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
            if [[ $(echo "$VERSION >= 3.9" | bc -l 2>/dev/null || echo "0") == "1" ]]; then
                PYTHON_CMD=$cmd
                break
            fi
        fi
    done
    
    if [ -z "$PYTHON_CMD" ]; then
        print_error "Python 3.9+ non trovato. Installazione in corso..."
        case $PACKAGE_MANAGER in
            "apt")
                sudo apt update
                sudo apt install -y python3.11 python3.11-pip python3.11-venv python3.11-dev
                PYTHON_CMD="python3.11"
                ;;
            "yum")
                sudo yum install -y python3.11 python3.11-pip python3.11-devel
                PYTHON_CMD="python3.11"
                ;;
            "brew")
                brew install python@3.11
                PYTHON_CMD="python3.11"
                ;;
            *)
                print_error "Installa Python 3.9+ manualmente e riprova"
                exit 1
                ;;
        esac
    fi
    
    print_success "Python disponibile: $PYTHON_CMD ($($PYTHON_CMD --version))"
    export PYTHON_CMD
}

# Installazione PostgreSQL
install_postgresql() {
    print_info "Controllo installazione PostgreSQL..."
    
    if ! command -v psql &> /dev/null; then
        print_warning "PostgreSQL non trovato. Installazione in corso..."
        case $PACKAGE_MANAGER in
            "apt")
                sudo apt update
                sudo apt install -y postgresql postgresql-contrib postgresql-server-dev-all
                sudo systemctl start postgresql
                sudo systemctl enable postgresql
                ;;
            "yum")
                sudo yum install -y postgresql-server postgresql-contrib postgresql-devel
                sudo postgresql-setup initdb
                sudo systemctl start postgresql
                sudo systemctl enable postgresql
                ;;
            "brew")
                brew install postgresql
                brew services start postgresql
                ;;
        esac
    else
        print_success "PostgreSQL già installato"
        
        # Verifica che il servizio sia attivo
        if command -v systemctl &> /dev/null; then
            if ! systemctl is-active --quiet postgresql; then
                print_info "Avvio servizio PostgreSQL..."
                sudo systemctl start postgresql
            fi
        fi
    fi
    
    print_success "PostgreSQL configurato"
}

# Configurazione database
setup_database() {
    print_info "Configurazione database Workly..."
    
    # Genera password casuale se non specificata
    DB_PASSWORD=${DB_PASSWORD:-$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)}
    
    # Crea database e utente
    sudo -u postgres psql -c "DROP DATABASE IF EXISTS workly_db;" 2>/dev/null || true
    sudo -u postgres psql -c "DROP USER IF EXISTS workly_user;" 2>/dev/null || true
    
    sudo -u postgres psql -c "CREATE DATABASE workly_db;"
    sudo -u postgres psql -c "CREATE USER workly_user WITH ENCRYPTED PASSWORD '$DB_PASSWORD';"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE workly_db TO workly_user;"
    sudo -u postgres psql -c "ALTER USER workly_user CREATEDB;"
    
    print_success "Database 'workly_db' creato"
    print_success "Utente 'workly_user' configurato"
    
    # Salva credenziali
    echo "DB_PASSWORD=$DB_PASSWORD" > .db_credentials
    chmod 600 .db_credentials
    
    export DB_PASSWORD
}

# Configurazione ambiente Python
setup_python_env() {
    print_info "Configurazione ambiente Python..."
    
    # Crea ambiente virtuale
    if [ ! -d "venv" ]; then
        $PYTHON_CMD -m venv venv
        print_success "Ambiente virtuale creato"
    fi
    
    # Attiva ambiente virtuale
    source venv/bin/activate
    
    # Aggiorna pip
    pip install --upgrade pip setuptools wheel
    
    # Installa dipendenze
    if [ -f "requirements.txt" ]; then
        print_info "Installazione dipendenze Python..."
        pip install -r requirements.txt
        print_success "Dipendenze Python installate"
    else
        print_warning "File requirements.txt non trovato, installazione dipendenze base..."
        pip install Flask Flask-Login Flask-SQLAlchemy Flask-WTF \
                    psycopg2-binary pandas openpyxl qrcode[pil] \
                    reportlab email-validator gunicorn defusedcsv \
                    Pillow PyJWT SQLAlchemy WTForms Werkzeug
    fi
}

# Configurazione file ambiente
setup_env_file() {
    print_info "Configurazione file ambiente..."
    
    # Genera chiavi segrete
    FLASK_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    SESSION_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    
    # Crea file .env
    cat > .env << EOF
# Database Configuration
DATABASE_URL=postgresql://workly_user:$DB_PASSWORD@localhost:5432/workly_db
PGHOST=localhost
PGPORT=5432
PGDATABASE=workly_db
PGUSER=workly_user
PGPASSWORD=$DB_PASSWORD

# Application Configuration
FLASK_SECRET_KEY=$FLASK_SECRET
FLASK_ENV=development
FLASK_DEBUG=True

# Session Configuration
SESSION_SECRET=$SESSION_SECRET

# Upload Configuration
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=52428800

# QR Configuration
QR_FOLDER=static/qr_codes
EOF
    
    chmod 600 .env
    print_success "File .env configurato"
}

# Creazione directory
create_directories() {
    print_info "Creazione directory necessarie..."
    
    mkdir -p uploads
    mkdir -p static/qr_codes
    mkdir -p instance
    mkdir -p logs
    
    chmod 755 uploads static/qr_codes instance logs
    
    print_success "Directory create"
}

# Inizializzazione database applicazione
init_app_database() {
    print_info "Inizializzazione database applicazione..."
    
    source venv/bin/activate
    
    # Controlla se i file Python esistono
    if [ ! -f "main.py" ] || [ ! -f "models.py" ]; then
        print_error "File applicazione mancanti. Assicurati di avere main.py e models.py"
        return 1
    fi
    
    # Inizializza database
    if [ -f "initialize_database.py" ]; then
        print_info "Usando script initialize_database.py..."
        python initialize_database.py
        if [ $? -ne 0 ]; then
            print_warning "Script initialize_database.py fallito, provo metodo alternativo..."
            python -c "
from main import app
with app.app_context():
    try:
        from models import db
        db.create_all()
        print('✓ Tabelle database create')
    except Exception as e:
        print(f'✗ Errore creazione tabelle: {e}')
        exit(1)
"
        fi
    else
        python -c "
from main import app
with app.app_context():
    try:
        from models import db
        db.create_all()
        print('✓ Tabelle database create')
    except Exception as e:
        print(f'✗ Errore creazione tabelle: {e}')
        exit(1)
"
    fi
    
    print_success "Database applicazione inizializzato"
}

# Popolamento dati test
populate_test_data() {
    print_info "Popolamento dati di test..."
    
    if [ -f "populate_test_data.py" ]; then
        source venv/bin/activate
        python populate_test_data.py
        print_success "Dati di test caricati"
    else
        print_warning "Script popolamento dati non trovato, salto..."
    fi
}

# Controllo finale
final_check() {
    print_info "Controllo finale installazione..."
    
    source venv/bin/activate
    pip list | grep -E "(Flask|SQLAlchemy|psycopg2)" > /dev/null
    if [ $? -eq 0 ]; then
        print_success "Dipendenze Python OK"
    else
        print_error "Problemi con dipendenze Python"
        return 1
    fi
    
    # Test connessione database
    python -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='localhost',
        database='workly_db',
        user='workly_user',
        password='$DB_PASSWORD'
    )
    conn.close()
    print('✓ Connessione database OK')
except Exception as e:
    print(f'✗ Errore connessione database: {e}')
    exit(1)
"
    
    print_success "Installazione completata con successo!"
}

# Creazione script avvio
create_start_script() {
    print_info "Creazione script di avvio..."
    
    cat > start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
export $(cat .env | xargs)
python main.py
EOF
    
    chmod +x start.sh
    
    cat > start_production.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
export $(cat .env | xargs)
gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 300 main:app
EOF
    
    chmod +x start_production.sh
    
    print_success "Script di avvio creati"
}

# Creazione servizio systemd (opzionale)
create_systemd_service() {
    if command -v systemctl &> /dev/null && [ "$OS" != "macos" ]; then
        read -p "Vuoi creare un servizio systemd per avvio automatico? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            INSTALL_DIR=$(pwd)
            USER=$(whoami)
            
            sudo tee /etc/systemd/system/workly.service > /dev/null << EOF
[Unit]
Description=Workly Platform
After=network.target postgresql.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 4 main:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF
            
            sudo systemctl daemon-reload
            sudo systemctl enable workly
            
            print_success "Servizio systemd creato (usa: sudo systemctl start workly)"
        fi
    fi
}

# Messaggi finali
show_final_instructions() {
    echo ""
    echo "=========================================="
    echo "   INSTALLAZIONE COMPLETATA!"
    echo "=========================================="
    echo ""
    print_success "Workly Platform è stato installato con successo!"
    echo ""
    echo -e "${BLUE}Per avviare l'applicazione:${NC}"
    echo "  ./start.sh                    # Modalità sviluppo"
    echo "  ./start_production.sh         # Modalità produzione"
    echo ""
    echo -e "${BLUE}Accesso Web:${NC}"
    echo "  URL: http://localhost:5000"
    echo ""
    echo -e "${BLUE}Credenziali di test:${NC}"
    echo "  Admin: admin / password123"
    echo "  Responsabile: mario.rossi / password123"
    echo "  Operatore: anna.bianchi / password123"
    echo ""
    echo -e "${BLUE}File importanti:${NC}"
    echo "  .env                          # Configurazione ambiente"
    echo "  .db_credentials               # Credenziali database"
    echo "  logs/workly.log               # Log applicazione"
    echo ""
    echo -e "${YELLOW}IMPORTANTE:${NC}"
    echo "- Cambia le password di default prima dell'uso in produzione"
    echo "- Backup regolare del database con: pg_dump workly_db > backup.sql"
    echo "- Per supporto consulta: INSTALLATION_GUIDE_LOCAL.md"
    echo ""
    
    if [ -f ".db_credentials" ]; then
        echo -e "${RED}Password database salvata in .db_credentials${NC}"
        echo -e "${RED}Conserva questo file in modo sicuro!${NC}"
    fi
}

# MAIN EXECUTION
main() {
    print_info "Inizio installazione Workly Platform..."
    
    detect_os
    check_permissions
    check_system_deps
    install_python
    install_postgresql
    setup_database
    create_directories
    setup_python_env
    setup_env_file
    init_app_database
    populate_test_data
    create_start_script
    final_check
    create_systemd_service
    show_final_instructions
    
    print_success "Installazione completata!"
}

# Gestione errori
trap 'print_error "Installazione interrotta"; exit 1' INT TERM

# Esegui installazione
main "$@"