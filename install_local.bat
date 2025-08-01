@echo off
setlocal EnableDelayedExpansion

REM =============================================================================
REM WORKLY - SCRIPT DI INSTALLAZIONE LOCALE PER WINDOWS
REM Sistema di Gestione Workforce con PostgreSQL
REM =============================================================================

echo ==================================================================================
echo                     WORKLY - INSTALLAZIONE LOCALE POSTGRESQL
echo ==================================================================================
echo.

REM Verifica che lo script sia eseguito dalla directory corretta
if not exist "main.py" (
    echo [ERRORE] Esegui lo script dalla directory principale del progetto Workly
    echo [ERRORE] Assicurati che i file main.py e models.py siano presenti
    pause
    exit /b 1
)

if not exist "models.py" (
    echo [ERRORE] File models.py non trovato nella directory corrente
    pause
    exit /b 1
)

echo [INFO] Directory corrente: %CD%
echo [INFO] Avvio installazione Workly con PostgreSQL...
echo.

REM =============================================================================
REM CONTROLLI PREREQUISITI
REM =============================================================================

echo [INFO] 1. Verifica prerequisiti sistema...

REM Controlla Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    python3 --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERRORE] Python 3.7+ non trovato. Installa Python 3.7 o superiore.
        echo [ERRORE] Scarica da: https://www.python.org/downloads/
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=python3
        for /f "tokens=2" %%i in ('python3 --version 2^>^&1') do set PYTHON_VERSION=%%i
    )
) else (
    set PYTHON_CMD=python
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
)

echo [OK] Python trovato: versione !PYTHON_VERSION!

REM Controlla pip
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRORE] pip non trovato. Installa pip per Python 3.
    pause
    exit /b 1
)
echo [OK] pip trovato

REM Controlla PostgreSQL
psql --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRORE] PostgreSQL non trovato.
    echo [ERRORE] Installa PostgreSQL prima di continuare:
    echo [ERRORE] Scarica da: https://www.postgresql.org/download/windows/
    pause
    exit /b 1
)

for /f "tokens=3" %%i in ('psql --version 2^>^&1') do set PG_VERSION=%%i
echo [OK] PostgreSQL trovato: versione !PG_VERSION!

echo.

REM =============================================================================
REM CONFIGURAZIONE AMBIENTE VIRTUALE
REM =============================================================================

echo [INFO] 2. Configurazione ambiente virtuale...

set VENV_DIR=.\workly_venv

if exist "%VENV_DIR%" (
    echo [WARN] Ambiente virtuale esistente trovato, lo rimuovo...
    rmdir /s /q "%VENV_DIR%"
)

echo [INFO] Creazione nuovo ambiente virtuale in: %VENV_DIR%
%PYTHON_CMD% -m venv "%VENV_DIR%"

REM Attiva ambiente virtuale
call "%VENV_DIR%\Scripts\activate.bat"
echo [OK] Ambiente virtuale attivato

REM Aggiorna pip nell'ambiente virtuale
echo [INFO] Aggiornamento pip nell'ambiente virtuale...
"%VENV_DIR%\Scripts\pip.exe" install --upgrade pip
echo [OK] pip aggiornato

echo.

REM =============================================================================
REM INSTALLAZIONE DIPENDENZE
REM =============================================================================

echo [INFO] 3. Installazione dipendenze Python...

if exist "requirements.txt" (
    echo [INFO] Installazione da requirements.txt...
    "%VENV_DIR%\Scripts\pip.exe" install -r requirements.txt
    echo [OK] Dipendenze installate da requirements.txt
) else (
    echo [INFO] requirements.txt non trovato, installazione dipendenze base...
    
    REM Dipendenze principali per PostgreSQL
    "%VENV_DIR%\Scripts\pip.exe" install "Flask>=2.3.0"
    "%VENV_DIR%\Scripts\pip.exe" install "Flask-Login>=0.6.0"
    "%VENV_DIR%\Scripts\pip.exe" install "Flask-SQLAlchemy>=3.0.0"
    "%VENV_DIR%\Scripts\pip.exe" install "Flask-WTF>=1.1.0"
    "%VENV_DIR%\Scripts\pip.exe" install "WTForms>=3.0.0"
    "%VENV_DIR%\Scripts\pip.exe" install "SQLAlchemy>=2.0.0"
    "%VENV_DIR%\Scripts\pip.exe" install "psycopg2-binary>=2.9.0"
    "%VENV_DIR%\Scripts\pip.exe" install "Werkzeug>=2.3.0"
    "%VENV_DIR%\Scripts\pip.exe" install "gunicorn>=20.1.0"
    "%VENV_DIR%\Scripts\pip.exe" install "python-dotenv>=1.0.0"
    "%VENV_DIR%\Scripts\pip.exe" install "Pillow>=9.0.0"
    "%VENV_DIR%\Scripts\pip.exe" install "openpyxl>=3.1.0"
    "%VENV_DIR%\Scripts\pip.exe" install "qrcode[pil]>=7.4.0"
    "%VENV_DIR%\Scripts\pip.exe" install "reportlab>=4.0.0"
    "%VENV_DIR%\Scripts\pip.exe" install "defusedcsv>=2.0.0"
    "%VENV_DIR%\Scripts\pip.exe" install "email-validator>=2.0.0"
    "%VENV_DIR%\Scripts\pip.exe" install "PyJWT>=2.6.0"
    
    echo [OK] Dipendenze base installate
)

echo.

REM =============================================================================
REM CONFIGURAZIONE DATABASE POSTGRESQL
REM =============================================================================

echo [INFO] 4. Configurazione database PostgreSQL...

echo.
echo [INFO] Inserisci le credenziali PostgreSQL:
set /p PG_HOST="Host PostgreSQL (default: localhost): "
if "%PG_HOST%"=="" set PG_HOST=localhost

set /p PG_PORT="Porta PostgreSQL (default: 5432): "
if "%PG_PORT%"=="" set PG_PORT=5432

set /p PG_DATABASE="Nome database (default: workly_db): "
if "%PG_DATABASE%"=="" set PG_DATABASE=workly_db

set /p PG_USER="Username PostgreSQL (default: postgres): "
if "%PG_USER%"=="" set PG_USER=postgres

set /p PG_PASSWORD="Password PostgreSQL: "

REM Test connessione PostgreSQL
echo [INFO] Test connessione PostgreSQL...
set PGPASSWORD=%PG_PASSWORD%

psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d postgres -c "\q" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRORE] Impossibile connettersi a PostgreSQL con le credenziali fornite
    echo [ERRORE] Verifica host, porta, username e password
    pause
    exit /b 1
)
echo [OK] Connessione PostgreSQL riuscita

REM Crea database se non esiste
echo [INFO] Creazione database '%PG_DATABASE%'...
psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d postgres -lqt | findstr /C:"%PG_DATABASE%" >nul
if %errorlevel% equ 0 (
    echo [WARN] Database '%PG_DATABASE%' già esistente
    set /p RECREATE_DB="Vuoi ricreare il database? (y/N): "
    if /i "!RECREATE_DB!"=="y" (
        psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d postgres -c "DROP DATABASE IF EXISTS %PG_DATABASE%;"
        psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d postgres -c "CREATE DATABASE %PG_DATABASE%;"
        echo [OK] Database ricreato
    ) else (
        echo [INFO] Utilizzo database esistente
    )
) else (
    psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d postgres -c "CREATE DATABASE %PG_DATABASE%;"
    echo [OK] Database '%PG_DATABASE%' creato
)

echo.

REM =============================================================================
REM CREAZIONE FILE DI CONFIGURAZIONE
REM =============================================================================

echo [INFO] 5. Creazione file di configurazione...

REM Crea directory config se non esiste
if not exist "config" mkdir "config"

REM Genera chiave segreta sicura
for /f %%i in ('python -c "import secrets; print(secrets.token_hex(32))"') do set SECRET_KEY=%%i

REM Crea file .env
echo # ============================================================================= > .env
echo # WORKLY - CONFIGURAZIONE AMBIENTE LOCALE POSTGRESQL >> .env
echo # ============================================================================= >> .env
echo. >> .env
echo # Database PostgreSQL >> .env
echo DATABASE_URL=postgresql://%PG_USER%:%PG_PASSWORD%@%PG_HOST%:%PG_PORT%/%PG_DATABASE% >> .env
echo PGHOST=%PG_HOST% >> .env
echo PGPORT=%PG_PORT% >> .env
echo PGDATABASE=%PG_DATABASE% >> .env
echo PGUSER=%PG_USER% >> .env
echo PGPASSWORD=%PG_PASSWORD% >> .env
echo. >> .env
echo # Flask Configuration >> .env
echo FLASK_SECRET_KEY=%SECRET_KEY% >> .env
echo SESSION_SECRET=%SECRET_KEY% >> .env
echo FLASK_ENV=production >> .env
echo FLASK_DEBUG=False >> .env
echo. >> .env
echo # Workly Configuration >> .env
echo WORKLY_ADMIN_EMAIL=admin@workly.local >> .env
echo WORKLY_COMPANY_NAME=Workly Platform >> .env
echo WORKLY_TIMEZONE=Europe/Rome >> .env
echo. >> .env
echo # Server Configuration >> .env
echo FLASK_HOST=127.0.0.1 >> .env
echo FLASK_PORT=5000 >> .env
echo WORKERS=4 >> .env

echo [OK] File .env creato

REM Crea script di avvio locale
echo @echo off > start_workly.bat
echo setlocal >> start_workly.bat
echo. >> start_workly.bat
echo REM ============================================================================= >> start_workly.bat
echo REM WORKLY - SCRIPT DI AVVIO LOCALE >> start_workly.bat
echo REM ============================================================================= >> start_workly.bat
echo. >> start_workly.bat
echo REM Verifica directory >> start_workly.bat
echo if not exist "main.py" ^( >> start_workly.bat
echo     echo [ERRORE] Esegui lo script dalla directory principale del progetto Workly >> start_workly.bat
echo     pause >> start_workly.bat
echo     exit /b 1 >> start_workly.bat
echo ^) >> start_workly.bat
echo. >> start_workly.bat
echo REM Attiva ambiente virtuale >> start_workly.bat
echo set VENV_DIR=.\workly_venv >> start_workly.bat
echo if not exist "%%VENV_DIR%%" ^( >> start_workly.bat
echo     echo [ERRORE] Ambiente virtuale non trovato. Esegui prima install_local.bat >> start_workly.bat
echo     pause >> start_workly.bat
echo     exit /b 1 >> start_workly.bat
echo ^) >> start_workly.bat
echo. >> start_workly.bat
echo call "%%VENV_DIR%%\Scripts\activate.bat" >> start_workly.bat
echo echo [INFO] Ambiente virtuale attivato >> start_workly.bat
echo. >> start_workly.bat
echo REM Carica variabili ambiente >> start_workly.bat
echo if not exist ".env" ^( >> start_workly.bat
echo     echo [ERRORE] File .env non trovato >> start_workly.bat
echo     pause >> start_workly.bat
echo     exit /b 1 >> start_workly.bat
echo ^) >> start_workly.bat
echo. >> start_workly.bat
echo REM Leggi variabili da .env >> start_workly.bat
echo for /f "usebackq tokens=1,2 delims==" %%%%a in ^(".env"^) do ^( >> start_workly.bat
echo     if not "%%%%a"=="" if not "%%%%a:~0,1"=="#" set %%%%a=%%%%b >> start_workly.bat
echo ^) >> start_workly.bat
echo echo [OK] Configurazione caricata da .env >> start_workly.bat
echo. >> start_workly.bat
echo REM Inizializza database se necessario >> start_workly.bat
echo echo [INFO] Inizializzazione database... >> start_workly.bat
echo "%%VENV_DIR%%\Scripts\python.exe" -c "from main import app; app.app_context().push(); from models import db; db.create_all(); print('[OK] Database inizializzato')" >> start_workly.bat
echo. >> start_workly.bat
echo REM Avvia server >> start_workly.bat
echo echo [INFO] Avvio Workly su http://%%FLASK_HOST%%:%%FLASK_PORT%% >> start_workly.bat
echo echo [INFO] Premi Ctrl+C per terminare >> start_workly.bat
echo echo. >> start_workly.bat
echo. >> start_workly.bat
echo "%%VENV_DIR%%\Scripts\python.exe" -m flask --app main run --host %%FLASK_HOST%% --port %%FLASK_PORT%% >> start_workly.bat

echo [OK] Script di avvio creato: start_workly.bat

echo.

REM =============================================================================
REM INIZIALIZZAZIONE DATABASE
REM =============================================================================

echo [INFO] 6. Inizializzazione database...

REM Imposta variabili ambiente per Flask
set DATABASE_URL=postgresql://%PG_USER%:%PG_PASSWORD%@%PG_HOST%:%PG_PORT%/%PG_DATABASE%
set FLASK_SECRET_KEY=%SECRET_KEY%
set SESSION_SECRET=%SECRET_KEY%

echo [INFO] Creazione tabelle database...

REM Inizializza database usando l'ambiente virtuale Python
"%VENV_DIR%\Scripts\python.exe" -c "import sys; import os; sys.path.insert(0, os.getcwd()); from main import app; app.app_context().push(); from models import db; db.create_all(); result = db.session.execute(db.text('SELECT 1')).scalar(); print('[OK] Database inizializzato e connessione verificata') if result == 1 else print('[ERRORE] Problema connessione database')"

if %errorlevel% neq 0 (
    echo [ERRORE] Errore durante l'inizializzazione del database
    pause
    exit /b 1
)

echo [OK] Database inizializzato correttamente

echo.

REM =============================================================================
REM CREAZIONE UTENTE AMMINISTRATORE
REM =============================================================================

echo [INFO] 7. Creazione utente amministratore...

echo.
echo [INFO] Inserisci i dati per l'utente amministratore:
set /p ADMIN_FIRST_NAME="Nome: "
set /p ADMIN_LAST_NAME="Cognome: "
set /p ADMIN_EMAIL="Email: "
set /p ADMIN_USERNAME="Username: "
set /p ADMIN_PASSWORD="Password: "

REM Crea utente admin
"%VENV_DIR%\Scripts\python.exe" -c "import sys; import os; sys.path.insert(0, os.getcwd()); from main import app; app.app_context().push(); from models import db, User, Role; from werkzeug.security import generate_password_hash; existing_user = User.query.filter_by(username='%ADMIN_USERNAME%').first(); existing_email = User.query.filter_by(email='%ADMIN_EMAIL%').first(); exit(1) if existing_user or existing_email else None; admin_role = Role.query.filter_by(name='Amministratore').first(); admin_role = admin_role or Role(name='Amministratore', description='Amministratore sistema con accesso completo', can_manage_users=True, can_view_all_users=True, can_edit_all_users=True, can_delete_users=True, can_manage_roles=True, can_view_attendance=True, can_edit_attendance=True, can_manage_shifts=True, can_view_all_shifts=True, can_create_shifts=True, can_edit_shifts=True, can_delete_shifts=True, can_manage_holidays=True, can_view_reports=True, can_export_data=True, can_manage_sedi=True, can_view_dashboard=True, can_manage_leave_requests=True, can_approve_leave_requests=True, can_view_leave_requests=True, can_create_leave_requests=True, can_manage_overtime_requests=True, can_approve_overtime_requests=True, can_view_overtime_requests=True, can_create_overtime_requests=True, can_manage_mileage_requests=True, can_approve_mileage_requests=True, can_view_mileage_requests=True, can_create_mileage_requests=True, can_manage_internal_messages=True, can_send_internal_messages=True, can_view_internal_messages=True, can_manage_aci_tables=True, can_view_aci_tables=True); db.session.add(admin_role); db.session.flush(); admin_user = User(first_name='%ADMIN_FIRST_NAME%', last_name='%ADMIN_LAST_NAME%', email='%ADMIN_EMAIL%', username='%ADMIN_USERNAME%', password_hash=generate_password_hash('%ADMIN_PASSWORD%'), is_active=True, all_sedi=True, role_id=admin_role.id); db.session.add(admin_user); db.session.commit(); print('[OK] Utente amministratore creato con successo')"

if %errorlevel% neq 0 (
    echo [ERRORE] Errore durante la creazione dell'utente amministratore
    echo [ERRORE] Probabilmente username o email già esistenti
    pause
    exit /b 1
)

echo [OK] Utente amministratore creato

echo.

REM =============================================================================
REM COMPLETAMENTO INSTALLAZIONE
REM =============================================================================

echo [OK] ==================================================================================
echo [OK]                     INSTALLAZIONE WORKLY COMPLETATA CON SUCCESSO!
echo [OK] ==================================================================================
echo.

echo [INFO] Configurazione:
echo [INFO]   • Database PostgreSQL: %PG_HOST%:%PG_PORT%/%PG_DATABASE%
echo [INFO]   • Ambiente virtuale: %VENV_DIR%
echo [INFO]   • Configurazione: .env
echo [INFO]   • Utente admin: %ADMIN_USERNAME% (%ADMIN_EMAIL%)
echo.

echo [INFO] Per avviare Workly:
echo [OK]   start_workly.bat
echo.

echo [INFO] Per accedere a Workly:
echo [OK]   http://127.0.0.1:5000
echo [OK]   Username: %ADMIN_USERNAME%
echo [OK]   Password: [quella inserita]
echo.

echo [WARN] Note importanti:
echo [WARN]   • Mantieni sicuro il file .env (contiene credenziali database)
echo [WARN]   • Per aggiornamenti, mantieni il database e ricrea solo l'ambiente virtuale
echo [WARN]   • Per backup: esporta il database PostgreSQL con pg_dump
echo.

echo [OK] Workly è pronto per l'uso!

pause