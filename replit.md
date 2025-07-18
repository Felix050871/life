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
- Role-based access control with 6 user types: Admin, Project Manager, Redattore, Sviluppatore, Operatore, Ente
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
- July 18, 2025: **Range Orari Flessibili** - Implementati range orari di entrata e uscita (start_time_min/max, end_time_min/max) sostituendo orari fissi, aggiornati modelli con metodi di visualizzazione range, form con validazioni, template con input group e JavaScript per sincronizzazione automatica min/max
- July 18, 2025: **Selezione Giorni Settimana Orari** - Aggiunto campo days_of_week al modello WorkSchedule, implementati preset (Lun-Ven, Sab-Dom, Tutti giorni, Personalizzato), aggiornati form e template con JavaScript per sincronizzazione automatica, visualizzazione giorni nella tabella orari
- July 18, 2025: **Miglioramenti UI Gestione Ruoli** - Risolti problemi di leggibilità con sfondo scuro per tutte le schede, rimosso permesso "Gestire Turni" dai template e dai ruoli Admin/Management, aggiornato forms.py per rimuovere can_manage_shifts
- July 18, 2025: **Progetto Workly Creato** - Clone completo e indipendente della piattaforma NS12 con branding generico "Workly Platform", rimosso logo aziendale, aggiornati tutti i template e riferimenti, creati README.md e configurazione .replit per deployment autonomo

## User Preferences

Preferred communication style: Simple, everyday language.