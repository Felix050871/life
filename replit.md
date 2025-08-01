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
- August 1, 2025: **Script Installazione Locale Corretti e Completati** - Risolti problemi critici negli script di installazione: corretto riferimento da classe `Role` a `UserRole` (modello corretto), aggiunto caricamento opzionale dati di test con `populate_test_data.py`, corretti token CSRF nascosti nei template, incluso `api_routes.py` mancante nel pacchetto, verifica completa di tutti i 9 file Python essenziali, script install_local.sh/bat ora completamente funzionanti per creazione utente amministratore e installazione completa
- August 1, 2025: **Pacchetto Installazione Locale PostgreSQL Rigenerato** - Creato nuovo pacchetto installazione completamente ottimizzato: eliminati riferimenti SQLite, utilizzati solo path relativi per ambiente virtuale e file, script install_local.sh/bat con controllo prerequisiti PostgreSQL, inizializzazione database corretta con verifica connessione, creazione automatica utente admin con ruolo completo, file .env con variabili PostgreSQL corrette, script avvio start_workly.sh/bat, documentazione completa README_INSTALLAZIONE_LOCALE.md, pacchetto tar.gz pronto per distribuzione (490KB), installazione completamente locale e portabile
- August 1, 2025: **Widget Dashboard Rimborsi Chilometrici Abilitati e Errori Risolti** - Attivati widget rimborsi chilometrici nel dashboard con correzione errori: rimossi commenti temporanei nella route dashboard, aggiunti widget "I Miei Rimborsi Chilometrici" e "Rimborsi Chilometrici Management", corretti attributi template (total_km, total_amount), aggiunto metodo get_route_list() nel modello MileageRequest, risolto errore logger mancante, widget dashboard e pagina visualizzazione rimborsi ora completamente funzionanti