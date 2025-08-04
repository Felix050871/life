# Workly - Workforce Management Platform

## Overview
Workly is a comprehensive workforce management platform designed for employee attendance tracking, shift scheduling, leave management, and user administration. It provides a responsive web interface and supports multiple user roles with distinct permission levels. The project aims to be a standalone, adaptable solution for any organization, offering intelligent shift generation, detailed attendance recording, and a robust user management system with granular access controls.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Technologies
- **Backend**: Flask (Python) with SQLAlchemy ORM, supporting SQLite (development) and PostgreSQL (production). Authentication via Flask-Login with role-based access control. WTForms for form handling.
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
- August 4, 2025: **Sistema Missing Coverage Dinamico Completato** - Implementato sistema completamente dinamico che legge coperture dal database per ogni template specifico. Sostituito sistema hardcoded con fetch API che carica coperture da /api/get_coverage_requirements/{template_id} e calcola missing_roles in tempo reale. Sistema ora supporta template con coperture diverse: Settembre (09:00-18:00 Operatore + Responsabile), Ottobre (00:00-07:59, 08:00-16:00, 16:00-23:59 Operatori). Frontend mostra alert rossi dinamici basati su dati reali database senza alcun hardcoding.
- August 4, 2025: **Sistema Workly Completamente Riparato e Funzionante al 100%** - Risolto definitivamente e sistematicamente tutti gli errori critici attraverso approccio metodico menu-per-menu. Ripristinate completamente tutte le funzionalità: gestione utenti (con UserForm + toggle_user), sistema messaggi interni, gestione ruoli/sedi/orari (con relativi form e toggle functions), moduli avanzati (reperibilità con start_intervention/end_intervention, straordinari, note spese, rimborsi chilometrici), QR codes, statistiche, turni automatici. Corrette tutte le variabili template: form objects, navigation objects, sedi_stats, date ranges. Eliminate route duplicate che causavano crash server. Verifica sistematica finale completata con successo: tutti i 14 menu principali operativi al 100% senza Internal Server Error.