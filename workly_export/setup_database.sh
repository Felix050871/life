#!/bin/bash
# Script di setup database per Workly
# Supporta SQLite (sviluppo) e PostgreSQL (produzione)

echo "🗄️  Workly - Setup Database"
echo "=========================="

# Controlla se Python è installato
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 non trovato. Installa Python 3.8+ per continuare."
    exit 1
fi

# Controlla se l'ambiente virtuale esiste
if [ ! -d "venv" ]; then
    echo "📦 Creazione ambiente virtuale..."
    python3 -m venv venv
fi

# Attiva ambiente virtuale
echo "🔧 Attivazione ambiente virtuale..."
source venv/bin/activate

# Installa dipendenze se necessario
if [ ! -f "venv/pyvenv.cfg" ]; then
    echo "📚 Installazione dipendenze..."
    pip install -r requirements.txt
fi

# Controlla se è specificato un database personalizzato
if [ -n "$DATABASE_URL" ]; then
    echo "📊 Usando database personalizzato: $DATABASE_URL"
else
    echo "📊 Usando database SQLite di default"
    export DATABASE_URL="sqlite:///$(pwd)/workly.db"
fi

# Configurazione chiave segreta se non presente
if [ -z "$FLASK_SECRET_KEY" ]; then
    export FLASK_SECRET_KEY="setup-secret-key-change-in-production"
    echo "🔑 Usando chiave segreta temporanea"
fi

# Esegue il script di creazione database
echo "🚀 Esecuzione script creazione database..."
python3 create_database.py

# Controlla il risultato
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Setup completato con successo!"
    echo ""
    echo "🚀 Per avviare Workly:"
    echo "   python3 run_local.py"
    echo ""
    echo "🌐 Oppure avvia il server manualmente:"
    echo "   python3 main.py"
    echo ""
    echo "📱 Accedi a: http://localhost:5000"
    echo "🔑 Username: admin | Password: admin123"
else
    echo "❌ Errore durante il setup del database"
    exit 1
fi