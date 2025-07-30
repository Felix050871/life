#!/bin/bash
# Workly - Setup Script per installazione automatica

set -e

echo "🚀 Workly Setup Script"
echo "======================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   error "This script should not be run as root"
fi

# Check system
check_system() {
    log "Checking system requirements..."
    
    # Check OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        log "Linux detected"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        log "macOS detected"
    else
        error "Unsupported operating system: $OSTYPE"
    fi
    
    # Check Python version
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        if [[ $(echo "$PYTHON_VERSION >= 3.11" | bc -l) -eq 1 ]]; then
            log "Python $PYTHON_VERSION found"
        else
            error "Python 3.11+ required, found $PYTHON_VERSION"
        fi
    else
        error "Python 3 not found"
    fi
    
    # Check Git
    if ! command -v git &> /dev/null; then
        error "Git not found"
    fi
    
    log "System requirements satisfied"
}

# Install system dependencies
install_dependencies() {
    log "Installing system dependencies..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Ubuntu/Debian
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y python3-venv python3-pip postgresql postgresql-contrib
        # CentOS/RHEL
        elif command -v yum &> /dev/null; then
            sudo yum install -y python3-venv python3-pip postgresql postgresql-server
        else
            warn "Package manager not recognized, please install dependencies manually"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS with Homebrew
        if command -v brew &> /dev/null; then
            brew install postgresql
        else
            warn "Homebrew not found, please install PostgreSQL manually"
        fi
    fi
    
    log "Dependencies installed"
}

# Setup virtual environment
setup_venv() {
    log "Setting up Python virtual environment..."
    
    if [[ -d "venv" ]]; then
        warn "Virtual environment already exists, removing..."
        rm -rf venv
    fi
    
    python3 -m venv venv
    source venv/bin/activate
    
    pip install --upgrade pip
    pip install -e .
    
    log "Virtual environment created and dependencies installed"
}

# Setup database
setup_database() {
    log "Setting up PostgreSQL database..."
    
    # Check if PostgreSQL is running
    if ! pgrep -x "postgres" > /dev/null; then
        warn "PostgreSQL not running, attempting to start..."
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            sudo systemctl start postgresql
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            brew services start postgresql
        fi
    fi
    
    # Create database and user
    read -p "Enter database name [workly]: " DB_NAME
    DB_NAME=${DB_NAME:-workly}
    
    read -p "Enter database user [workly_user]: " DB_USER
    DB_USER=${DB_USER:-workly_user}
    
    read -s -p "Enter database password: " DB_PASS
    echo
    
    sudo -u postgres psql << EOF
CREATE DATABASE $DB_NAME;
CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASS';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
ALTER USER $DB_USER CREATEDB;
\q
EOF
    
    # Create .env file
    cat > .env << EOF
DATABASE_URL=postgresql://$DB_USER:$DB_PASS@localhost/$DB_NAME
FLASK_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
FLASK_ENV=development
DEBUG=True
PORT=5000
EOF
    
    chmod 600 .env
    log "Database setup completed"
}

# Populate test data
populate_data() {
    log "Populating test data..."
    
    source venv/bin/activate
    python populate_test_data.py
    
    log "Test data populated successfully"
}

# Setup systemd service (Linux only)
setup_service() {
    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        warn "Systemd service setup only available on Linux"
        return
    fi
    
    read -p "Setup systemd service? [y/N]: " setup_service
    if [[ $setup_service =~ ^[Yy]$ ]]; then
        log "Setting up systemd service..."
        
        APP_DIR=$(pwd)
        USER=$(whoami)
        
        sudo tee /etc/systemd/system/workly.service > /dev/null << EOF
[Unit]
Description=Workly Workforce Management
After=network.target postgresql.service

[Service]
Type=exec
User=$USER
Group=$USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 main:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
        
        sudo systemctl daemon-reload
        sudo systemctl enable workly
        
        log "Systemd service created. Use 'sudo systemctl start workly' to start"
    fi
}

# Main setup function
main() {
    log "Starting Workly setup..."
    
    check_system
    
    read -p "Install system dependencies? [y/N]: " install_deps
    if [[ $install_deps =~ ^[Yy]$ ]]; then
        install_dependencies
    fi
    
    setup_venv
    
    read -p "Setup database? [y/N]: " setup_db
    if [[ $setup_db =~ ^[Yy]$ ]]; then
        setup_database
    fi
    
    read -p "Populate test data? [y/N]: " populate_test
    if [[ $populate_test =~ ^[Yy]$ ]]; then
        populate_data
    fi
    
    setup_service
    
    log "Setup completed successfully!"
    log ""
    log "Next steps:"
    log "1. Activate virtual environment: source venv/bin/activate"
    log "2. Start application: python main.py"
    log "3. Open browser: http://localhost:5000"
    log "4. Login with: admin / password123"
    log ""
    log "For production deployment, see DEPLOYMENT_GUIDE.md"
}

# Run main function
main "$@"