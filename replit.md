# Workly - Workforce Management Platform

## Overview
Workly is a comprehensive workforce management platform built with Flask, designed for employee attendance tracking, shift scheduling, leave management, and user administration. It supports multiple user roles with distinct permission levels and provides a responsive web interface for managing workforce operations. The project aims to be a standalone, adaptable solution for any organization, derived from the NS12 Workforce Management Platform but re-branded as "Workly Platform" to ensure generic applicability. It offers key capabilities such as intelligent shift generation, detailed attendance recording, and a robust user management system with granular access controls.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Technologies
- **Backend**: Flask (Python) with SQLAlchemy ORM, supporting SQLite (development) and PostgreSQL (production). Authentication is handled via Flask-Login with role-based access control. WTForms is used for form handling.
- **Frontend**: Jinja2 templating, Bootstrap 5 (dark theme) with custom CSS, vanilla JavaScript for interactivity, and Font Awesome for icons. The design adopts a mobile-first responsive approach.
- **Deployment**: Gunicorn WSGI server, configured for autoscale deployment.

### Key Architectural Decisions & Features
- **Database Schema**: Core entities include User (with roles and part-time percentages), AttendanceEvent (detailed clock-in/out and breaks), LeaveRequest, Shift, ReperibilitaShift (on-call duties), and ReperibilitaIntervention (on-call interventions).
- **User Management**: Features a permission-based access control system with over 30 granular permissions. It defines 5 standard roles (Amministratore, Responsabile, Supervisore, Operatore, Ospite) whose permissions are dynamically configurable by administrators. Supports advanced work schedule assignments (ORARIA vs. TURNI modes), multi-sede access, and secure password hashing.
- **Attendance Tracking**: Comprehensive clock-in/out, break tracking, daily records with notes, historical viewing, and reporting. Includes a static QR code system for quick attendance marking, with intelligent user status validation to prevent duplicate entries.
- **Shift Management**: Supports intelligent shift generation with workload balancing, recurring shift patterns via templates, and integration with leave and part-time percentages. Includes on-call duty management and intervention tracking.
- **Mileage Reimbursement System**: A complete system for managing mileage reimbursement requests, including automatic distance and amount calculation using ACI tables, multi-point routes, and a manager approval workflow. Features integration with user vehicle assignments and granular permissions.
- **UI/UX**: Emphasizes a modern, responsive design with a dark Bootstrap theme. All NS12 branding has been replaced with generic "Workly" branding. Features include global Bootstrap modals for confirmations, optimized overlay system with specific feedback for long operations (e.g., Excel exports), and an updated sidebar navigation with dynamic submenus based on user permissions.
- **Data Export**: Full conversion from CSV to Excel (.xlsx) exports across all modules (attendance, shifts, reports, expense notes) using `openpyxl` server-side and `SheetJS` client-side.
- **System Logging and Optimization**: Systematic code cleanup for security, performance, and maintainability, including replacing `print()` statements with professional logging, removing obsolete files, and centralizing configuration.
- **Dashboard Widgets**: Dynamic dashboard widgets for displaying team statistics, personal leave requests, shifts, on-call duties, and mileage reimbursements, all controlled by granular user permissions.
- **Internal Messaging**: Multi-recipient internal messaging system with permission-based sending and automatic notifications for approvals/rejections, categorized by message type.
- **User Profile Management**: Separate user profile system allowing users to modify personal details independently from admin user management.

## External Dependencies
- **PostgreSQL**: Production database.
- **SQLite**: Development database.
- **Font Awesome**: Icon library.
- **Bootstrap 5**: Frontend framework.
- **Flask-Login**: User session management.
- **WTForms / Flask-WTF**: Form handling and validation.
- **SQLAlchemy**: ORM for database interaction.
- **Gunicorn**: WSGI server for production deployment.
- **Werkzeug**: Password hashing.
- **Openpyxl**: Python library for server-side Excel file generation.
- **SheetJS (XLSX)**: JavaScript library for client-side Excel handling.

## Recent Changes
- August 1, 2025: **Sistema Generazione Turni Migliorato - Coperture 24h e Divisione Intelligente** - Rimosso limite 16h, ora supporta coperture fino a 24h. Implementata logica intelligente di divisione automatica turni: calcola orario massimo lavorabile per utente (8h per 100%, proporzionale per part-time), divide automaticamente coperture eccedenti su più utenti, algoritmo bilanciamento carichi avanzato considera capacità individuale utenti. Funzioni: get_user_max_daily_hours(), split_coverage_into_segments_by_user_capacity() per distribuzione ottimale coperture lunghe
- August 1, 2025: **Menu Ferie/Permessi Completamente Riorganizzato** - Creata struttura menu distinta con route specifiche: "Richiedi Ferie/Permessi" → create_leave_request_page, "Le Mie Richieste" → leave_requests?view=my, "Approva Richieste" → leave_requests?view=approve, "Visualizza Richieste" → leave_requests?view=view. Sistema mostra contenuto appropriato in base a modalità e permessi utente
- August 1, 2025: **Sistema Permessi Admin Abilitato con Protezione** - Admin può ora modificare tutti i permessi eccetto quelli critici (can_manage_roles, can_manage_users) per sicurezza. Template edit_role.html mostra campi protetti come disabled con icona lucchetto. Sistema previene lockout admin mantenendo accesso gestione sistema
- August 1, 2025: **Script Completi Creazione Database Generati** - Creati script automatici per generare database con struttura corretta: script SQL completo (16KB) con tutte le 26 tabelle e campi attuali, script Python initialize_database.py per inizializzazione sicura, documentazione completa README_DATABASE_CREATION.md, script compatibili con campo 'active' (non 'is_active'), aggiornati script installazione per usare nuovi script database, pacchetto completo "workly-complete-with-database-scripts" pronto per distribuzione
- August 1, 2025: **Script Installazione Completamente Corretti e Verificati** - Risolti tutti i problemi di compatibilità database negli script installazione: corretto import `from main import app` in install.bat/sh, aggiornato `from models import db` per inizializzazione corretta, sostituito `is_active=True` con `active=True` in install_local.bat/sh, verificata compatibilità con modello User corrente, creato nuovo pacchetto installazione locale "workly-local-installation-corrected-20250801.tar.gz" (489KB) con tutti gli script completamente aggiornati e funzionanti
- August 1, 2025: **Script populate_test_data.py Completamente Rigenerato** - Risolti tutti gli errori di compatibilità con la struttura database: corretti campi per tutti i modelli (User, Sede, AttendanceEvent, LeaveRequest, OvertimeRequest, InternalMessage, Shift, Holiday), aggiornati riferimenti da `is_active` a `active`, corretti vincoli NOT NULL, creazione dati coerente con schema PostgreSQL attuale, script ora funziona perfettamente creando 22 utenti, 1.261 presenze, 54 richieste ferie, 60 straordinari, 36 messaggi, 62 turni, 14 festività, password test standard "Password123!"
- August 1, 2025: **Export Database PostgreSQL Completo Creato** - Sviluppato script automatico per export completo database: 1.168 record da 26 tabelle, file SQL (367KB) con struttura e dati, archivio compresso tar.gz (36KB), script bash create_database_export.sh per export automatico, istruzioni complete per importazione in nuovi ambienti PostgreSQL, export pronto per distribuzione e backup
- August 1, 2025: **Script Installazione Locale Corretti e Completati** - Risolti problemi critici negli script di installazione: corretto riferimento da classe `Role` a `UserRole` (modello corretto), aggiunto caricamento opzionale dati di test con `populate_test_data.py`, corretti token CSRF nascosti nei template, incluso `api_routes.py` mancante nel pacchetto, verifica completa di tutti i 9 file Python essenziali, script install_local.sh/bat ora completamente funzionanti per creazione utente amministratore e installazione completa
- August 1, 2025: **Pacchetto Installazione Locale PostgreSQL Rigenerato** - Creato nuovo pacchetto installazione completamente ottimizzato: eliminati riferimenti SQLite, utilizzati solo path relativi per ambiente virtuale e file, script install_local.sh/bat con controllo prerequisiti PostgreSQL, inizializzazione database corretta con verifica connessione, creazione automatica utente admin con ruolo completo, file .env con variabili PostgreSQL corrette, script avvio start_workly.sh/bat, documentazione completa README_INSTALLAZIONE_LOCALE.md, pacchetto tar.gz pronto per distribuzione (490KB), installazione completamente locale e portabile
- August 1, 2025: **Widget Dashboard Rimborsi Chilometrici Abilitati e Errori Risolti** - Attivati widget rimborsi chilometrici nel dashboard con correzione errori: rimossi commenti temporanei nella route dashboard, aggiunti widget "I Miei Rimborsi Chilometrici" e "Rimborsi Chilometrici Management", corretti attributi template (total_km, total_amount), aggiunto metodo get_route_list() nel modello MileageRequest, risolto errore logger mancante, widget dashboard e pagina visualizzazione rimborsi ora completamente funzionanti
- August 1, 2025: **Standardizzazione Completa Campo 'active' vs 'is_active'** - Risolto completamente l'inconsistenza terminologica: standardizzato su 'active' in tutto il progetto (database PostgreSQL, modelli, forms, routes, templates, script). Eliminati 95+ riferimenti 'is_active' obsoleti, applicazione ora completamente coerente e funzionante senza errori 500. Database: 11 tabelle usano 'active', codice Python e templates allineati, tutti i forms convertiti da BooleanField('is_active') a BooleanField('active')