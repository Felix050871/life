@echo off
setlocal enabledelayedexpansion

:: Workly Platform - Script Installazione Automatica Windows
:: Versione: 1.0
:: Data: 31 Luglio 2025

echo ==========================================
echo    WORKLY PLATFORM INSTALLER v1.0
echo ==========================================
echo.

:: Controllo permessi amministratore
net file 1>nul 2>nul
if not %errorlevel% == 0 (
    echo [ERRORE] Questo script richiede permessi di amministratore.
    echo Fai clic destro e seleziona "Esegui come amministratore"
    pause
    exit /b 1
)

:: Variabili globali
set PYTHON_CMD=
set DB_PASSWORD=%RANDOM%%RANDOM%%RANDOM%
set INSTALL_DIR=%~dp0

echo [INFO] Directory installazione: %INSTALL_DIR%

:: Controllo Python
echo [INFO] Controllo installazione Python...

:: Cerca Python installato
for %%i in (python.exe python3.exe python3.11.exe python3.10.exe python3.9.exe) do (
    where %%i >nul 2>&1
    if !errorlevel! == 0 (
        for /f "tokens=2" %%v in ('%%i --version 2^>^&1') do (
            echo [INFO] Trovato %%i versione %%v
            set PYTHON_CMD=%%i
            goto :python_found
        )
    )
)

:python_not_found
echo [ERRORE] Python 3.9+ non trovato!
echo.
echo Scarica e installa Python da: https://www.python.org/downloads/
echo Assicurati di selezionare "Add Python to PATH" durante l'installazione
echo.
pause
exit /b 1

:python_found
echo [OK] Python disponibile: %PYTHON_CMD%

:: Controllo PostgreSQL
echo [INFO] Controllo installazione PostgreSQL...
where psql >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRORE] PostgreSQL non trovato!
    echo.
    echo Scarica e installa PostgreSQL da: https://www.postgresql.org/download/windows/
    echo Ricorda la password dell'utente 'postgres' durante l'installazione
    echo.
    pause
    exit /b 1
)
echo [OK] PostgreSQL disponibile

:: Controllo servizio PostgreSQL
sc query postgresql-x64-14 >nul 2>&1
if %errorlevel% neq 0 (
    sc query postgresql-x64-13 >nul 2>&1
    if !errorlevel! neq 0 (
        sc query postgresql-x64-12 >nul 2>&1
        if !errorlevel! neq 0 (
            echo [WARNING] Servizio PostgreSQL non trovato. Assicurati che sia in esecuzione.
        )
    )
)

:: Creazione ambiente virtuale
echo [INFO] Configurazione ambiente Python...
if not exist "venv" (
    %PYTHON_CMD% -m venv venv
    if %errorlevel% neq 0 (
        echo [ERRORE] Impossibile creare ambiente virtuale
        pause
        exit /b 1
    )
    echo [OK] Ambiente virtuale creato
)

:: Attivazione ambiente virtuale
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERRORE] Impossibile attivare ambiente virtuale
    pause
    exit /b 1
)

:: Aggiornamento pip
echo [INFO] Aggiornamento pip...
python -m pip install --upgrade pip setuptools wheel
if %errorlevel% neq 0 (
    echo [WARNING] Problemi aggiornamento pip, continuo...
)

:: Installazione dipendenze
echo [INFO] Installazione dipendenze Python...
if exist "requirements.txt" (
    pip install -r requirements.txt
) else (
    echo [INFO] requirements.txt non trovato, installazione dipendenze base...
    pip install Flask Flask-Login Flask-SQLAlchemy Flask-WTF psycopg2-binary pandas openpyxl qrcode[pil] reportlab email-validator gunicorn defusedcsv Pillow PyJWT SQLAlchemy WTForms Werkzeug
)
if %errorlevel% neq 0 (
    echo [ERRORE] Installazione dipendenze fallita
    pause
    exit /b 1
)
echo [OK] Dipendenze Python installate

:: Configurazione database
echo [INFO] Configurazione database...
set /p POSTGRES_PASSWORD="Inserisci la password dell'utente 'postgres' di PostgreSQL: "

:: Creazione database e utente
echo DROP DATABASE IF EXISTS workly_db; | psql -h localhost -U postgres -W
echo DROP USER IF EXISTS workly_user; | psql -h localhost -U postgres -W
echo CREATE DATABASE workly_db; | psql -h localhost -U postgres -W
echo CREATE USER workly_user WITH ENCRYPTED PASSWORD '%DB_PASSWORD%'; | psql -h localhost -U postgres -W
echo GRANT ALL PRIVILEGES ON DATABASE workly_db TO workly_user; | psql -h localhost -U postgres -W
echo ALTER USER workly_user CREATEDB; | psql -h localhost -U postgres -W

if %errorlevel% neq 0 (
    echo [ERRORE] Configurazione database fallita
    echo Verifica che PostgreSQL sia in esecuzione e che la password sia corretta
    pause
    exit /b 1
)
echo [OK] Database configurato

:: Creazione directory
echo [INFO] Creazione directory...
if not exist "uploads" mkdir uploads
if not exist "static\qr_codes" mkdir static\qr_codes
if not exist "instance" mkdir instance
if not exist "logs" mkdir logs
echo [OK] Directory create

:: Generazione chiavi segrete
echo [INFO] Generazione configurazione...
python -c "import secrets; print('FLASK_SECRET=' + secrets.token_hex(32))" > temp_secrets.txt
python -c "import secrets; print('SESSION_SECRET=' + secrets.token_hex(32))" >> temp_secrets.txt

:: Lettura chiavi generate
for /f "tokens=2 delims==" %%a in ('findstr "FLASK_SECRET" temp_secrets.txt') do set FLASK_SECRET=%%a
for /f "tokens=2 delims==" %%a in ('findstr "SESSION_SECRET" temp_secrets.txt') do set SESSION_SECRET=%%a
del temp_secrets.txt

:: Creazione file .env
echo # Database Configuration > .env
echo DATABASE_URL=postgresql://workly_user:%DB_PASSWORD%@localhost:5432/workly_db >> .env
echo PGHOST=localhost >> .env
echo PGPORT=5432 >> .env
echo PGDATABASE=workly_db >> .env
echo PGUSER=workly_user >> .env
echo PGPASSWORD=%DB_PASSWORD% >> .env
echo. >> .env
echo # Application Configuration >> .env
echo FLASK_SECRET_KEY=%FLASK_SECRET% >> .env
echo FLASK_ENV=development >> .env
echo FLASK_DEBUG=True >> .env
echo. >> .env
echo # Session Configuration >> .env
echo SESSION_SECRET=%SESSION_SECRET% >> .env
echo. >> .env
echo # Upload Configuration >> .env
echo UPLOAD_FOLDER=uploads >> .env
echo MAX_CONTENT_LENGTH=52428800 >> .env
echo. >> .env
echo # QR Configuration >> .env
echo QR_FOLDER=static/qr_codes >> .env

echo [OK] File .env creato

:: Salvataggio credenziali database
echo DB_PASSWORD=%DB_PASSWORD% > .db_credentials
echo [OK] Credenziali database salvate in .db_credentials

:: Inizializzazione database applicazione
echo [INFO] Inizializzazione database applicazione...
if exist "main.py" (
    python -c "from main import app; app.app_context().push(); from models import db; db.create_all(); print('[OK] Database inizializzato')"
    if !errorlevel! neq 0 (
        echo [ERRORE] Inizializzazione database fallita
        pause
        exit /b 1
    )
) else (
    echo [WARNING] main.py non trovato, salta inizializzazione database
)

:: Popolamento dati test
echo [INFO] Popolamento dati di test...
if exist "populate_test_data.py" (
    python populate_test_data.py
    echo [OK] Dati di test caricati
) else (
    echo [WARNING] populate_test_data.py non trovato, salta...
)

:: Creazione script di avvio
echo [INFO] Creazione script di avvio...

:: Script avvio sviluppo
echo @echo off > start.bat
echo cd /d "%%~dp0" >> start.bat
echo call venv\Scripts\activate.bat >> start.bat
echo python main.py >> start.bat
echo pause >> start.bat

:: Script avvio produzione
echo @echo off > start_production.bat
echo cd /d "%%~dp0" >> start.bat
echo call venv\Scripts\activate.bat >> start_production.bat
echo gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 300 main:app >> start_production.bat
echo pause >> start_production.bat

echo [OK] Script di avvio creati

:: Test finale
echo [INFO] Test finale installazione...
python -c "import flask, sqlalchemy, psycopg2; print('[OK] Dipendenze principali verificate')"
if %errorlevel% neq 0 (
    echo [ERRORE] Test dipendenze fallito
    pause
    exit /b 1
)

:: Test connessione database
python -c "import psycopg2; conn = psycopg2.connect(host='localhost', database='workly_db', user='workly_user', password='%DB_PASSWORD%'); conn.close(); print('[OK] Connessione database verificata')"
if %errorlevel% neq 0 (
    echo [ERRORE] Test connessione database fallito
    pause
    exit /b 1
)

:: Messaggio finale
echo.
echo ==========================================
echo    INSTALLAZIONE COMPLETATA!
echo ==========================================
echo.
echo [OK] Workly Platform installato con successo!
echo.
echo Per avviare l'applicazione:
echo   start.bat                    ^(Modalità sviluppo^)
echo   start_production.bat         ^(Modalità produzione^)
echo.
echo Accesso Web:
echo   URL: http://localhost:5000
echo.
echo Credenziali di test:
echo   Admin: admin / password123
echo   Responsabile: mario.rossi / password123
echo   Operatore: anna.bianchi / password123
echo.
echo File importanti:
echo   .env                         ^(Configurazione ambiente^)
echo   .db_credentials              ^(Credenziali database^)
echo   logs\workly.log              ^(Log applicazione^)
echo.
echo IMPORTANTE:
echo - Cambia le password di default prima dell'uso in produzione
echo - Backup regolare del database
echo - Per supporto consulta: INSTALLATION_GUIDE_LOCAL.md
echo.
echo Password database salvata in .db_credentials
echo Conserva questo file in modo sicuro!
echo.

pause