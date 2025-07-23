# Workly - Workforce Management Platform

## Overview

Workly is a comprehensive workforce management platform built with Flask, designed to handle employee attendance tracking, shift scheduling, leave management, and user administration. The system supports multiple user roles with different permission levels and provides a responsive web interface for managing all aspects of workforce operations.

## Project Origin

Workly is derived from the NS12 Workforce Management Platform, created as an independent development branch for enhanced customization and feature development. All NS12-specific branding has been replaced with generic "Workly Platform" branding to create a standalone product.

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Database**: SQLAlchemy ORM with support for both SQLite (development) and PostgreSQL (production)
- **Authentication**: Flask-Login for session management with role-based access control
- **Forms**: WTForms with Flask-WTF for form handling and validation
- **Deployment**: Gunicorn WSGI server with autoscale deployment target

### Frontend Architecture
- **Templates**: Jinja2 templating engine with Bootstrap dark theme
- **Styling**: Bootstrap 5 with custom CSS overrides
- **JavaScript**: Vanilla JavaScript for enhanced interactivity
- **Icons**: Font Awesome for consistent iconography
- **Responsive Design**: Mobile-first approach with Bootstrap grid system

### Database Schema
The application uses SQLAlchemy models with the following key entities:
- **User**: Stores user information, roles, and part-time percentages
- **AttendanceEvent**: Tracks multiple daily attendance events (clock-in/out, breaks) with timestamp precision
- **LeaveRequest**: Manages vacation and leave requests
- **Shift**: Handles shift assignments and scheduling
- **ReperibilitaShift**: Manages on-call duty assignments
- **ReperibilitaIntervention**: Tracks on-call interventions with priority levels

## Key Features

### User Management System
- **Permission-based access control** with granular 30+ permissions for each menu functionality
- **Dynamic role management** with 5 standardized roles:
  - **Amministratore**: Full system access with all permissions
  - **Responsabile**: Local site management with operational functions
  - **Supervisore**: Global site supervision with view-only access
  - **Operatore**: Standard operational access to core functions
  - **Ospite**: Limited access for external users
- **Admin-configurable permissions**: Each role's permissions can be dynamically managed
- User creation, modification, and deactivation capabilities
- Part-time percentage tracking for specific roles
- Secure password hashing with Werkzeug

### Attendance Tracking
- Clock-in/out functionality with timestamp recording
- Break time tracking (start/end)
- Daily attendance records with notes capability
- Historical attendance viewing and reporting
- QR code system for quick attendance marking

### Shift Management
- Intelligent shift generation with workload balancing
- Template system for recurring shift patterns
- Integration with leave requests and part-time percentages
- On-call (reperibilità) duty management with intervention tracking

### QR Code System
- Static QR code generation for deployment flexibility
- Dedicated QR pages for entry/exit tracking
- Admin controls for regenerating QR codes when server changes
- Fallback to external API when static files unavailable

## Branding Changes from NS12

### Visual Changes
- Removed NS12 logo from login page
- Replaced with Workly branding using briefcase icon
- Updated all page titles from "NS12 S.p.A." to "Workly"
- Changed footer attribution to "Workly Platform"

### Generic Branding
- No company-specific references in user interface
- Suitable for deployment by any organization
- Maintains professional appearance with generic workforce management theme

## Deployment Configuration

### Development Environment
- SQLite database for local development
- Flask development server with debug mode
- Hot reload capability for rapid development

### Production Environment
- Gunicorn WSGI server with multiple workers
- PostgreSQL database with connection pooling
- Environment variable configuration for secrets
- Autoscale deployment target on Replit

## Recent Changes
- July 23, 2025: **Dashboard Layout Riorganizzata e Sistema Widget Completo** - Layout dashboard completamente riorganizzato con struttura più compatta e intuitiva: sezione presenze personali centralizzata, statistiche e gestione in riga, attività in card più piccole, sezione reperibilità dedicata, accessi rapidi per admin/manager. Implementato sistema completo 7 permessi widget dashboard (team stats, presenze personali, gestione team, richieste ferie, presenze giornaliere, coperture turni, reperibilità) con controllo granulare admin tramite gestione ruoli
- July 23, 2025: **Sistema Modifica Turni Intelligente Completato** - Implementato sistema completo di modifica turni con filtro intelligente: estrazione automatica data turno dal DOM, filtro utenti disponibili per data specifica escludendo già impegnati, visualizzazione nomi completi invece di username, gestione CSRF corretta, refresh automatico dopo modifica con mantenimento vista template, debug completo per troubleshooting
- July 23, 2025: **Sistema Turni Automatici Completo** - Sostituito completamente vecchio sistema turni manuale con nuovo sistema automatico basato su template presidio: implementata route turni_automatici con generazione automatica da PresidioCoverageTemplate, eliminati campi data manuali (ora prelevate automaticamente dal template), aggiornato menu navigazione con "Gestione Template Presidio", "Turni Automatici", "Visualizza Presidi", sistema intelligente di selezione ruoli e bilanciamento carichi di lavoro
- July 22, 2025: **Sistema Gestione Coperture Presidio Completo** - Implementato sistema completo gestione coperture: creazione nuove coperture con template create_presidio_coverage, generazione/rigenerazione turni automatica da template, interfaccia selezione ruoli interattiva con checkbox e quantità, validazione sovrapposizioni periodi, aggiornate informazioni funzionalità nella gestione coperture, sistema completamente funzionale per creazione template e generazione turni
- July 22, 2025: **Sistema Visualizzazione/Modifica Template Presidio Completo** - Implementate funzionalità complete per template coperture presidio: route view_presidio_coverage e edit_presidio_coverage, template dedicati con visualizzazione orari/pause separati, form modifica con validazione JavaScript per pause, logica backend per salvataggio modifiche con parsing ruoli, lista template semplificata senza orari (variano per giorno), corretta denominazione "Sede Turni"
- July 22, 2025: **Correzione Gestione Coperture Presidio** - Risolti errori 500 in "Gestione Coperture": corretto uso modello PresidioCoverage per coperture di presidio (non ReperibilitaCoverage per reperibilità), aggiornati titoli da "reperibilità" a "presidio", corretti link azioni per funzionalità presidio, sistema ora mostra correttamente template coperture presidio raggruppati per periodo
- July 21, 2025: **Menu Turni Riorganizzato in 3 Funzionalità** - Implementata nuova struttura menu Turni: 1) Gestione Coperture (gestione coperture presidio per sede), 2) Gestione Turni (creazione/modifica turni esistente), 3) Visualizza Turni (visualizzazione read-only per copertura selezionata), aggiunti permessi granulari can_manage_coverage/can_view_coverage, creati template dedicati, supporto completo multi-sede, admin ora vede correttamente sottomenu Gestione Coperture
- July 21, 2025: **Sistema Turni Completo Multi-Sede Funzionante** - Risolto completamente accesso turni per utenti multi-sede: menu Turni visibile e funzionante, route /shifts mostra 25 turni esistenti per admin/supervisore, template di turnazione visualizzabili (creato esempio "Template Agosto 2025"), sistema completo con statistiche turni, calendario e gestione avanzata, supporto dinamico per utenti all_sedi e sede-specifici
- July 21, 2025: **Menu Turni Dinamico per Utenti Multi-Sede** - Risolto accesso menu turni per utenti all_sedi: aggiornato can_access_shifts_menu() per supportare utenti multi-sede, creato metodo get_turni_sedi() per gestione dinamica accesso sedi turni, aggiornate route manage_turni, generate_turnazioni e shifts per utilizzo logica unificata, sistema ora supporta utenti globali con accesso a tutte le sedi turni
- July 21, 2025: **Sistema Presenze Dinamico per Sede Completato** - Implementato sistema completo per visualizzazione presenze per sede: supporto utenti all_sedi (multi-sede), permessi granulari can_access_attendance e can_view_attendance, pulsanti dinamici "Le Mie"/"Sede" configurabili dall'admin, risolto accesso per utenti Supervisore con accesso globale, sistema completamente dinamico basato su permessi
- July 21, 2025: **Controlli Turni Basati su Modalità Sede** - Implementati controlli completi per nascondere menu e funzionalità turni quando sede non supporta modalità "Turni": menu navigazione condizionato, route protette con validazione sede, template con messaggi informativi, sistema completamente dinamico basato su sede.is_turni_mode()
- July 21, 2025: **Correzione Errori Menu Turni** - Risolti errori 500 nel menu turni: corretti tutti riferimenti endpoint da presidio_coverage a reperibilita_coverage, implementati controlli condizionali nel template, aggiunta validazione sede per tutte le route di gestione turni
- July 21, 2025: **Protezione Amministratore** - Implementata protezione completa contro cancellazione/disattivazione dell'utente amministratore: bloccata route toggle_user, aggiunto controllo nel form di modifica, disabilitato checkbox nel template edit_user.html, sostituito pulsante toggle con icona "protetto" nell'interfaccia utente
- July 21, 2025: **Statistiche Utenti per Ruolo in Dashboard** - Aggiunta sezione "Statistiche Utenti" nella dashboard che mostra il numero di utenti per ogni ruolo con colori specifici (Amministratore: rosso, Responsabile: blu, Supervisore: giallo, Operatore: azzurro, Ospite: grigio), implementata logica backend in get_team_statistics()
- July 21, 2025: **Eliminazione Riferimenti Fissi ai Ruoli** - Rimossi tutti i riferimenti hardcoded ai ruoli obsoleti (Admin, Management, Ente, Staff, etc.) da template e route, sostituiti con controlli dinamici basati sui permessi, implementato metodo has_role() per controlli specifici sui ruoli quando necessario
- July 21, 2025: **Sistema All_Sedi Implementato** - Aggiunto campo all_sedi al database utenti, aggiornati form e template per gestire accesso globale a tutte le sedi, implementata logica di validazione e JavaScript per gestione interazione tra campi sede specifica e accesso globale
- July 21, 2025: **Dashboard Admin Pulita** - Rimossa sezione registrazione presenze (Entrata/Uscita/Pausa/Ripresa) per amministratori, aggiornati controlli per escludere ruolo 'Amministratore' dalle funzionalità operative, mantenute solo funzioni di gestione e supervisione
- July 21, 2025: **Sistema Permessi Granulari Completo** - Implementato sistema completo di 30+ permessi granulari per ogni funzionalità del menu (gestione/visualizzazione), eliminati tutti i riferimenti ai vecchi ruoli legacy, creati 5 nuovi ruoli standardizzati: Amministratore, Responsabile, Supervisore, Operatore, Ospite con permessi specifici
- July 21, 2025: **Controlli Autorizzazione Basati su Permessi** - Migrate tutte le route da controlli diretti sui ruoli a metodi granulari di permesso (can_manage_users, can_view_shifts, etc.), aggiornato menu di navigazione con ordine specificato: Home - Ruoli - Utenti - Sedi - Orari - Turni - Reperibilità - Festività - Gestione QR - Statistiche
- July 18, 2025: **Range Orari Flessibili** - Implementati range orari di entrata e uscita (start_time_min/max, end_time_min/max) sostituendo orari fissi, aggiornati modelli con metodi di visualizzazione range, form con validazioni, template con input group e JavaScript per sincronizzazione automatica min/max
- July 18, 2025: **Selezione Giorni Settimana Orari** - Aggiunto campo days_of_week al modello WorkSchedule, implementati preset (Lun-Ven, Sab-Dom, Tutti giorni, Personalizzato), aggiornati form e template con JavaScript per sincronizzazione automatica, visualizzazione giorni nella tabella orari
- July 18, 2025: **Sistema Controllo Orari Sede con Permessi** - Implementato controllo intelligente entrate/uscite basato su orari sede invece di turni, considera permessi approvati per calcolo ritardi/anticipi, aggiornato modello LeaveRequest con campi start_time/end_time per permessi orari
- July 18, 2025: **Progetto Workly Creato** - Clone completo e indipendente della piattaforma NS12 con branding generico "Workly Platform", rimosso logo aziendale, aggiornati tutti i template e riferimenti, creati README.md e configurazione .replit per deployment autonomo

## User Preferences

Preferred communication style: Simple, everyday language.