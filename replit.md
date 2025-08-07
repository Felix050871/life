# Workly - Workforce Management Platform

## Overview
Workly is a comprehensive workforce management platform designed for employee attendance tracking, shift scheduling, leave management, and user administration. It provides a responsive web interface and supports multiple user roles with distinct permission levels. The project aims to be a standalone, adaptable solution for any organization, offering intelligent shift generation, detailed attendance recording, and a robust user management system with granular access controls.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Technologies
- **Backend**: Flask (Python) with SQLAlchemy ORM using PostgreSQL exclusively. Authentication via Flask-Login with role-based access control. WTForms for form handling.
- **Frontend**: Jinja2 templating, Bootstrap 5 (dark theme) with custom CSS, vanilla JavaScript for interactivity, and Font Awesome for icons. Mobile-first responsive design.
- **Deployment**: Gunicorn WSGI server.

### Key Architectural Decisions & Features
- **Database Schema**: Core entities include User (with roles and part-time percentages), AttendanceEvent, LeaveRequest, Shift, ReperibilitaShift (on-call duties), and ReperibilitaIntervention (on-call interventions).
- **User Management**: Features a permission-based access control system with over 30 granular permissions. Defines 5 standard roles whose permissions are dynamically configurable. Supports advanced work schedule assignments (ORARIA vs. TURNI modes) and multi-sede access.
- **Attendance Tracking**: Comprehensive clock-in/out, break tracking, daily records, historical viewing, and reporting. Includes a static QR code system for quick attendance marking with intelligent user status validation.
- **Shift Management**: Supports intelligent shift generation with workload balancing, recurring shift patterns via templates, and integration with leave/part-time percentages. Includes on-call duty management and intervention tracking. The system adheres to strict operational safety rules, including no overlaps, mandatory 11-hour rest periods after night shifts, splitting shifts longer than 8 hours, and automatic workload balancing. It handles 24/7 coverage, calculates maximum work hours per user, ensures weekly rest days, and prevents inappropriate consecutive assignments.
- **Mileage Reimbursement System**: Manages mileage reimbursement requests, including automatic distance/amount calculation using ACI tables, multi-point routes, and a manager approval workflow. Integrates with user vehicle assignments and granular permissions.
- **UI/UX**: Modern, responsive design with a dark Bootstrap theme. Uses generic "Workly" branding. Features global Bootstrap modals for confirmations, an optimized overlay system for long operations, and updated sidebar navigation with dynamic submenus based on user permissions.
- **Data Export**: Supports conversion from CSV to Excel (.xlsx) across all modules using `openpyxl` server-side and `SheetJS` client-side.
- **System Logging and Optimization**: Professional logging, removal of obsolete files, and centralized configuration for security, performance, and maintainability.
- **Dashboard Widgets**: Dynamic widgets for team statistics, personal leave requests, shifts, on-call duties, and mileage reimbursements, controlled by user permissions.
- **Internal Messaging**: Multi-recipient internal messaging system with permission-based sending and automatic notifications for approvals/rejections.
- **User Profile Management**: Separate user profile system allowing users to modify personal details independently.

## External Dependencies
- **PostgreSQL**: Database (required).
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
- August 7, 2025: **Sistema Permessi Form RoleForm Completato** - Aggiunti campi mancanti can_view_my_reperibilita, can_view_my_attendance, can_view_my_leave alla classe RoleForm in forms.py. Corrette etichette "Widget Le Mie Note Spese" in "Visualizzare Le Mie Note Spese". Implementati campi nei metodi get_permissions_dict() e populate_permissions(). Database aggiornato per tutti i ruoli con nuovi permessi. Ora tutti i permessi "my" sono visibili e modificabili nella pagina di gestione ruoli.
- August 7, 2025: **Sistema Permessi Standardizzato Completamente** - Implementata standardizzazione completa del sistema permessi per distinguere esplicitamente tra "Visualizzare Tutti" vs "Visualizzare Le Mie". Aggiunti nuovi permessi `can_view_my_reperibilita`, `can_view_my_attendance`, `can_view_my_leave` e aggiornata logica nelle routes per usare permessi espliciti invece di controlli nel codice. Tutti i ruoli esistenti aggiornati automaticamente. Ora ogni modulo ha distinzione chiara e consistente tra dati personali e dati di tutti. Sistema più flessibile e manutenibile con logica centralizzata nei permessi.
- August 7, 2025: **Sistema Permessi 1:1 Implementato Completamente** - Rimossa completamente logica gerarchica dai permessi. Implementato sistema 1:1 dove ogni permesso corrisponde esattamente a una voce di menu. Corretto metodo `has_permission` per controllo diretto senza logica manage-include-view. Corretti tutti i template (user_management.html, manage_roles.html, manage_sedi.html, manage_work_schedules.html) rimuovendo controlli AND che richiedevano sia can_manage_* che can_view_*. Ora chi ha can_manage_* può accedere a tutte le funzioni di gestione senza dover avere anche can_view_*.
- August 7, 2025: **Sistema Database Semplificato per Solo PostgreSQL** - Rimosso supporto SQLite e semplificato sistema per usare esclusivamente PostgreSQL. Aggiornati config.py, app.py e create_database.py per richiedere DATABASE_URL obbligatoriamente. Script di creazione database ottimizzato per PostgreSQL con controlli di validazione. Sistema ora più robusto e adatto per deployment professionale.
- August 5, 2025: **Reports Charts Functionality Restored** - Risolto problema grafici vuoti "Andamento presenze" e "Distribuzione ruoli" nella pagina reports. Aggiunta libreria Chart.js mancante nel template, implementata gestione errori per dati vuoti, aggiunti console.log per debug e messaggi informativi per grafici senza dati. Corrette variabili template per compatibilità con chart_data. Grafici ora mostrano correttamente dati di presenza giornaliera e distribuzione ruoli utenti attivi.
- August 4, 2025: **Sistema Missing Coverage Dinamico Completato** - Implementato sistema completamente dinamico che legge coperture dal database per ogni template specifico. Sostituito sistema hardcoded con fetch API che carica coperture da /api/get_coverage_requirements/{template_id} e calcola missing_roles in tempo reale. Sistema ora supporta template con coperture diverse: Settembre (09:00-18:00 Operatore + Responsabile), Ottobre (00:00-07:59, 08:00-16:00, 16:00-23:59 Operatori). Frontend mostra alert rossi dinamici basati su dati reali database senza alcun hardcoding.