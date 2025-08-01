#!/bin/bash

# =============================================================================
# SCRIPT PER CREARE PACCHETTO INSTALLAZIONE LOCALE WORKLY
# =============================================================================

echo "Creazione pacchetto installazione locale Workly..."

# Nome del pacchetto
PACKAGE_NAME="workly-local-installation-$(date +%Y%m%d)"
TEMP_DIR="/tmp/$PACKAGE_NAME"

# Crea directory temporanea
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"

echo "Directory temporanea: $TEMP_DIR"

# Copia file principali applicazione
echo "Copiando file applicazione..."
cp app.py "$TEMP_DIR/"
cp main.py "$TEMP_DIR/"
cp models.py "$TEMP_DIR/"
cp routes.py "$TEMP_DIR/"
cp api_routes.py "$TEMP_DIR/"
cp forms.py "$TEMP_DIR/"
cp utils.py "$TEMP_DIR/"
cp config.py "$TEMP_DIR/"
cp requirements.txt "$TEMP_DIR/"
cp pyproject.toml "$TEMP_DIR/" 2>/dev/null || true
cp populate_test_data.py "$TEMP_DIR/" 2>/dev/null || true

# Copia directory
echo "Copiando directory..."
cp -r static "$TEMP_DIR/" 2>/dev/null || mkdir "$TEMP_DIR/static"
cp -r templates "$TEMP_DIR/" 2>/dev/null || mkdir "$TEMP_DIR/templates"
mkdir -p "$TEMP_DIR/instance"

# Copia script di installazione
echo "Copiando script installazione..."
cp install_local.sh "$TEMP_DIR/"
cp install_local.bat "$TEMP_DIR/"
cp README_INSTALLAZIONE_LOCALE.md "$TEMP_DIR/"

# Copia documentazione
echo "Copiando documentazione..."
cp README.md "$TEMP_DIR/" 2>/dev/null || echo "# Workly Platform" > "$TEMP_DIR/README.md"
cp replit.md "$TEMP_DIR/" 2>/dev/null || true
cp VERSION.md "$TEMP_DIR/" 2>/dev/null || echo "1.0.0" > "$TEMP_DIR/VERSION.md"

# Crea file .gitignore per installazione locale
cat > "$TEMP_DIR/.gitignore" << 'EOF'
# Ambiente virtuale
workly_venv/
venv/
env/

# File configurazione sensibili
.env
.env.local
.env.production

# Database locale
*.db
*.sqlite
*.sqlite3

# Log
*.log
logs/

# Cache Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Backup
*.bak
*.backup
backup_*

# Test
.coverage
.pytest_cache/
test_*.py
tests/
EOF

# Crea file LEGGIMI con istruzioni rapide
cat > "$TEMP_DIR/LEGGIMI.txt" << 'EOF'
===============================================================================
                          WORKLY - INSTALLAZIONE LOCALE
===============================================================================

REQUISITI:
- Python 3.7+
- PostgreSQL 12+

INSTALLAZIONE RAPIDA:

1. Windows:
   - Doppio click su: install_local.bat
   - Segui le istruzioni a schermo
   - Avvia con: start_workly.bat

2. Linux/macOS:
   - chmod +x install_local.sh
   - ./install_local.sh
   - Segui le istruzioni a schermo
   - Avvia con: ./start_workly.sh

3. Accesso:
   - http://127.0.0.1:5000
   - Username/Password: quelli inseriti durante installazione

4. Dati di Test (Opzionale):
   - python populate_test_data.py
   - Aggiunge utenti, turni e dati di esempio per testare il sistema

DOCUMENTAZIONE COMPLETA:
- Leggi README_INSTALLAZIONE_LOCALE.md per dettagli completi

CARATTERISTICHE:
✅ Installazione completamente locale con path relativi
✅ Ambiente virtuale isolato 
✅ Database PostgreSQL (no SQLite)
✅ Configurazione automatica
✅ Script avvio semplificati
✅ Gestione completa workforce management

SUPPORTO:
Per problemi, consulta la sezione Troubleshooting nel README.

===============================================================================
EOF

# Crea archivio compresso
echo "Creazione archivio..."
cd /tmp
tar -czf "$PACKAGE_NAME.tar.gz" "$PACKAGE_NAME"

# Sposta nella directory corrente
mv "$PACKAGE_NAME.tar.gz" "$OLDPWD/"

# Pulizia
rm -rf "$TEMP_DIR"

echo "✓ Pacchetto creato: $PACKAGE_NAME.tar.gz"
echo "✓ Dimensione: $(du -h "$PACKAGE_NAME.tar.gz" | cut -f1)"
echo ""
echo "Per distribuire:"
echo "1. Invia il file $PACKAGE_NAME.tar.gz"
echo "2. L'utente deve estrarre: tar -xzf $PACKAGE_NAME.tar.gz"
echo "3. Entrare nella directory: cd $PACKAGE_NAME"  
echo "4. Eseguire: ./install_local.sh (Linux/macOS) o install_local.bat (Windows)"