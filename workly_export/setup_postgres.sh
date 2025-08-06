#!/bin/bash
# Script automatico per setup PostgreSQL e creazione database Workly

echo "🐘 Workly - Setup PostgreSQL Database"
echo "====================================="

# Funzione per controllare se PostgreSQL è installato
check_postgres() {
    if ! command -v psql &> /dev/null; then
        echo "❌ PostgreSQL non trovato."
        echo "💡 Installa PostgreSQL:"
        echo "   Ubuntu/Debian: sudo apt-get install postgresql postgresql-contrib"
        echo "   CentOS/RHEL: sudo yum install postgresql-server postgresql-contrib"
        echo "   macOS: brew install postgresql"
        echo "   Windows: Scarica da https://www.postgresql.org/download/"
        exit 1
    fi
}

# Funzione per controllare se il servizio PostgreSQL è attivo
check_postgres_service() {
    if ! sudo systemctl is-active --quiet postgresql 2>/dev/null && ! brew services list | grep -q "postgresql.*started" 2>/dev/null; then
        echo "🔧 Avvio servizio PostgreSQL..."
        if command -v systemctl &> /dev/null; then
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
        elif command -v brew &> /dev/null; then
            brew services start postgresql
        fi
    fi
}

# Funzione per creare database e utente
create_database() {
    local db_name="workly"
    local db_user="workly_user"
    local db_password
    
    # Genera password casuale se non specificata
    if [ -z "$WORKLY_DB_PASSWORD" ]; then
        db_password=$(openssl rand -base64 16)
        echo "🔐 Password generata automaticamente: $db_password"
    else
        db_password="$WORKLY_DB_PASSWORD"
        echo "🔐 Usando password specificata"
    fi
    
    echo "📊 Creazione database $db_name..."
    
    # Sostituisci la password nel file SQL
    sed "s/workly_secure_password_change_me/$db_password/g" create_postgres_db.sql > temp_db_script.sql
    
    # Esegui script SQL
    if sudo -u postgres psql -f temp_db_script.sql > /dev/null 2>&1; then
        echo "✅ Database creato con successo!"
    else
        echo "⚠️  Database potrebbe già esistere, continuando..."
    fi
    
    # Pulisci file temporaneo
    rm -f temp_db_script.sql
    
    # Mostra stringa di connessione
    echo ""
    echo "🔗 Stringa di connessione DATABASE_URL:"
    echo "postgresql://$db_user:$db_password@localhost:5432/$db_name"
    echo ""
    echo "💾 Salva questa informazione nel file .env:"
    echo "DATABASE_URL=postgresql://$db_user:$db_password@localhost:5432/$db_name"
    
    # Aggiorna automaticamente .env se esiste
    if [ -f ".env" ]; then
        if grep -q "DATABASE_URL=" .env; then
            sed -i.bak "s|DATABASE_URL=.*|DATABASE_URL=postgresql://$db_user:$db_password@localhost:5432/$db_name|" .env
            echo "✅ File .env aggiornato automaticamente"
        else
            echo "DATABASE_URL=postgresql://$db_user:$db_password@localhost:5432/$db_name" >> .env
            echo "✅ DATABASE_URL aggiunto a .env"
        fi
    elif [ -f ".env.example" ]; then
        cp .env.example .env
        sed -i.bak "s|DATABASE_URL=.*|DATABASE_URL=postgresql://$db_user:$db_password@localhost:5432/$db_name|" .env
        echo "✅ File .env creato e configurato"
    fi
    
    return 0
}

# Funzione per testare connessione
test_connection() {
    local db_url
    if [ -f ".env" ] && grep -q "DATABASE_URL=" .env; then
        db_url=$(grep "DATABASE_URL=" .env | cut -d'=' -f2)
        echo "🧪 Test connessione database..."
        
        if python3 -c "
import os
import sys
sys.path.append('.')
os.environ['DATABASE_URL'] = '$db_url'
os.environ['FLASK_SECRET_KEY'] = 'test'
try:
    from app import app, db
    with app.app_context():
        db.engine.execute('SELECT 1')
    print('✅ Connessione database OK')
except Exception as e:
    print(f'❌ Errore connessione: {e}')
    sys.exit(1)
        " 2>/dev/null; then
            echo "🎉 Database configurato correttamente!"
            return 0
        else
            echo "⚠️  Problemi di connessione, verifica la configurazione"
            return 1
        fi
    else
        echo "⚠️  File .env non trovato o DATABASE_URL non configurato"
        return 1
    fi
}

# Menu principale
show_menu() {
    echo ""
    echo "Cosa vuoi fare?"
    echo "1) Setup completo automatico (consigliato)"
    echo "2) Solo crea database PostgreSQL"
    echo "3) Solo inizializza dati con Python"
    echo "4) Test connessione database"
    echo "5) Esci"
    echo ""
    read -p "Scelta [1-5]: " choice
    
    case $choice in
        1)
            check_postgres
            check_postgres_service
            create_database
            echo ""
            echo "🚀 Inizializzazione dati..."
            python3 create_database.py
            echo ""
            echo "🎉 Setup completo completato!"
            ;;
        2)
            check_postgres
            check_postgres_service
            create_database
            ;;
        3)
            echo "🚀 Inizializzazione dati Python..."
            python3 create_database.py
            ;;
        4)
            test_connection
            ;;
        5)
            echo "👋 Arrivederci!"
            exit 0
            ;;
        *)
            echo "❌ Scelta non valida"
            show_menu
            ;;
    esac
}

# Main
main() {
    # Controlla se siamo nella directory giusta
    if [ ! -f "create_database.py" ]; then
        echo "❌ File create_database.py non trovato."
        echo "💡 Esegui questo script dalla directory workly_export"
        exit 1
    fi
    
    # Controlla parametri
    if [ "$1" = "--auto" ]; then
        echo "🤖 Modalità automatica attivata"
        check_postgres
        check_postgres_service
        create_database
        python3 create_database.py
        echo "🎉 Setup automatico completato!"
    else
        show_menu
    fi
}

# Esegui main
main "$@"