# Life - Comprehensive Multi-Tenant SAAS Platform

## Overview
Life is a comprehensive multi-tenant SAAS workforce management platform consisting of two integrated sections:
- **FLOW**: "Il tuo gestore smart del tempo" - L'area dedicata all'organizzazione operativa del team, alla pianificazione dei turni, alla richiesta di ferie e permessi e al tracciamento di presenze e straordinari. Meno burocrazia, più produttività. *Tagline: Semplifica il lavoro, moltiplica il tempo. ⏱️*
- **CIRCLE**: "Il centro della tua community aziendale" - Lo spazio di connessione social per rimanere aggiornato sulle iniziative, accedere velocemente ai documenti e agli strumenti di lavoro, e condividere idee con i colleghi. *Tagline: Connettiti alle persone, connettiti al lavoro. 🤝*

The platform provides a responsive web interface with multiple user roles and distinct permission levels. It's designed as a **path-based multi-tenant system** serving various companies, each with isolated data, custom branding, and dedicated URL paths (`/t/<slug>`).

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Technologies
- **Backend**: Flask (Python) with SQLAlchemy ORM, PostgreSQL, Flask-Login for authentication (role-based access control), and WTForms for form handling.
- **Frontend**: Jinja2 templating, Bootstrap 5 (dark theme) with custom CSS, vanilla JavaScript for interactivity, and Font Awesome for icons. Mobile-first responsive design.
- **Deployment**: Gunicorn WSGI server.

### Platform Sections
1. **FLOW** - "Il tuo gestore smart del tempo"
   - **Tagline**: Semplifica il lavoro, moltiplica il tempo. ⏱️
   - **Description**: L'area dedicata all'organizzazione operativa del team, alla pianificazione dei turni, alla richiesta di ferie e permessi e al tracciamento di presenze e straordinari. Meno burocrazia, più produttività.
   - **Features**:
     - Attendance tracking with clock-in/out
     - Intelligent shift scheduling and management
     - Leave request workflow
     - Overtime and mileage reimbursements
     - Banca ore (time bank) system
     - On-call duty management (Reperibilità)
     - Reports and data export

2. **CIRCLE** - "Il centro della tua community aziendale"
   - **Tagline**: Connettiti alle persone, connettiti al lavoro. 🤝
   - **Description**: Lo spazio di connessione social per rimanere aggiornato sulle iniziative, accedere velocemente ai documenti e agli strumenti di lavoro, e condividere idee con i colleghi.
   - **Features**:
     - News feed and announcements (post system with comments/likes)
     - Delorean (company history archive)
     - Groups (department, project, interest-based)
     - Polls and surveys
     - Company calendar with events
     - Document management (Quality/HR documents)
     - Tool links (quick access to external tools like Trello, Email, etc.)
     - Personas (employee directory with social profiles)
     - Tech Feed (IT/technology updates)

### Key Architectural Decisions & Features
- **Multi-Tenant SaaS System**: Fully implemented as a Software-as-a-Service platform with complete company isolation and role-based administration.
  - **Path-Based Multi-Tenancy**: Each company has a dedicated URL path (`/t/<slug>`) for complete isolation
    - SUPERADMIN login: `/admin/login` for system administrators
    - Tenant login: `/t/<slug>/login` with company-specific branding and logo
    - Custom unauthorized handler redirects users to appropriate login based on context
    - Middleware (`middleware_tenant.py`) extracts slug from URL, loads Company into flask.g, validates user access
  - **SUPERADMIN Role**: System-level administrators (`is_system_admin=true`, `company_id=null`) manage the entire SaaS platform
    - Create and manage companies via "Amministrazione Sistema" menu at `/admin/login`
    - Mandatory creation of company ADMIN during company setup (transactional workflow)
    - Cannot access company-specific operational data (sedi, users, shifts, etc.)
  - **Company ADMIN Role**: Each company has its own administrator (`role='Amministratore'`, linked to specific `company_id`)
    - Full control over their company's configuration (sedi, users, mail settings, etc.)
    - Cannot access other companies' data or create new companies
    - Auto-assigned `all_sedi=true` for full location access within their company
  - **Data Isolation**: All core entities include `company_id` foreign key: User, AttendanceEvent, LeaveRequest, Shift, ShiftTemplate, Holiday, InternalMessage, Intervention, ReperibilitaShift, ReperibilitaCoverage, ReperibilitaTemplate, ReperibilitaIntervention, OvertimeRequest, MileageRequest, ExpenseReport, ExpenseCategory, WorkSchedule, ACITable, LeaveType, OvertimeType, PresidioCoverageTemplate, PresidioCoverage
  - **Username/Email Scoping**: User credentials (username, email) are unique per company, not globally
    - Database constraints: `UniqueConstraint('company_id', 'username')` and `UniqueConstraint('company_id', 'email')`
    - Allows same username/email across different companies
    - SUPERADMIN credentials (company_id=NULL) handled separately
  - **Helper Utilities**: `utils_tenant.py` provides `filter_by_company()` for automatic query filtering, `set_company_on_create()` for automatic company assignment, and `get_user_company_id()` for retrieving user's company
  - **Complete Multi-Tenant Security**: ALL 15 blueprints fully implement multi-tenant filtering with 100+ database queries secured:
    - ✅ interventions.py, messages.py, reperibilita.py
    - ✅ user_management.py, dashboard.py, reports.py + utils.py
    - ✅ banca_ore.py, export.py, qr.py, api.py
    - ✅ aci.py, presidio.py, holidays.py, admin.py, expense.py
    - ✅ attendance.py, leave.py, shifts.py
  - **Company Creation Workflow**: SUPERADMIN creates company with mandatory admin user and unique slug in single transaction; validates unique codes, slugs, usernames, and emails
- **User Management**: Features a permission-based access control system with over 70 granular permissions (including 19 CIRCLE-specific permissions) and 5 dynamically configurable standard roles. Supports advanced work schedule assignments (ORARIA vs. TURNI modes) and multi-location access. Enhanced user profiles include social fields (bio, LinkedIn, phone, department, job title) for CIRCLE integration. The role management page includes a dedicated CIRCLE permissions card for easy configuration of social intranet access and management capabilities.
- **Attendance Tracking**: Includes clock-in/out, break tracking, daily records, historical viewing, reporting, and a static QR code system for quick attendance marking with intelligent user status validation.
- **Shift Management**: Supports intelligent shift generation with workload balancing, recurring shift patterns via templates, and integration with leave/part-time percentages. Includes on-call duty management (`ReperibilitaShift`) and intervention tracking (`ReperibilitaIntervention`). Adheres to operational safety rules (e.g., no overlaps, 11-hour rest periods, split shifts for long durations, 24/7 coverage, weekly rest days).
- **Mileage Reimbursement System**: Manages mileage reimbursement requests, including automatic distance/amount calculation using ACI tables, multi-point routes, and a manager approval workflow.
- **UI/UX**: Modern, responsive dark-themed Bootstrap design with generic "Life" branding. Features global Bootstrap modals, an optimized overlay system, and dynamic sidebar navigation based on user permissions. Company ADMIN users (role='Amministratore', not SUPERADMIN) have dedicated "Amministrazione" dropdown in the topbar with Ruoli and Utenti links, visually separated from FLOW/CIRCLE tabs - these menus are hidden from the sidebar for a cleaner interface.
- **Data Export**: Supports CSV to Excel (.xlsx) conversion across all modules using `openpyxl` (server-side) and `SheetJS` (client-side).
- **System Logging and Optimization**: Professional logging, configuration centralization for security, performance, and maintainability.
- **Dashboard Widgets**: Dynamic widgets for team statistics, personal leave requests, shifts, on-call duties, and mileage reimbursements, controlled by user permissions.
- **Internal Messaging**: Multi-recipient internal messaging system with permission-based sending and automatic notifications for approvals/rejections.
- **User Profile Management**: Allows users to modify personal details independently, including profile image upload with automatic resizing to 200x200px, and CIRCLE social fields (bio, LinkedIn URL, phone number, department, job title). Profile images are displayed in a circular format in the navbar and profile page, with a default image for users without a custom photo.
- **CIRCLE Social Features**: Complete social intranet implementation with 8 core models (CirclePost, CircleGroup, CirclePoll, CircleDocument, CircleCalendarEvent, CircleComment, CircleLike, CircleToolLink) and 6 dedicated blueprints. Features include news/announcement posting with engagement (comments, likes), group management, polling system, company calendar, document repository with versioning, and customizable tool links dashboard. All CIRCLE entities enforce multi-tenant isolation via company_id filtering.
  - **Email Notifications for Announcements**: When creating a "comunicazione" (announcement) post, users can optionally send email notifications to all active company users via a checkbox. Uses multi-tenant email system with HTML-formatted emails containing a direct link to the announcement.
- **Multi-Tenant Email System**: Hybrid SMTP architecture supporting both global (SUPERADMIN) and per-company email configurations
  - **Architecture**: 
    - SUPERADMIN uses global SMTP (environment variables) for onboarding/activation emails when creating new companies
    - Each tenant uses CompanyEmailSettings for operational emails (notifications, approvals, announcements)
    - EmailContext class auto-detects correct SMTP based on g.company (tenant context) with fallback to global config
  - **Security**: SMTP passwords encrypted at rest using Fernet symmetric encryption (cryptography library)
    - Encryption key derived from environment ENCRYPTION_KEY or SESSION_SECRET (dev fallback)
    - CompanyEmailSettings.set_password() encrypts, get_decrypted_password() decrypts on-the-fly
  - **Admin UI**: Company ADMIN can configure SMTP settings via "Amministrazione > Configurazione Email"
    - Form with server, port, TLS/SSL, credentials, sender, reply-to fields
    - Test email functionality to validate configuration
    - Status tracking (last_tested_at, test_status, test_error)
  - **Implementation Files**:
    - `models.py`: CompanyEmailSettings model with encrypted credentials
    - `utils_encryption.py`: Fernet-based encryption/decryption utilities
    - `email_utils.py`: EmailContext, send_email_smtp() for direct SMTP, auto-detection logic
    - `blueprints/admin.py`: Routes for email_settings, test_email
    - `blueprints/companies.py`: Welcome email sent to company admin upon creation (uses global SMTP)
  - **Integration**: All existing email notifications (leave approvals, overtime, announcements) automatically use appropriate SMTP context
- **Database Simplification**: System is exclusively designed for PostgreSQL, removing previous SQLite support for robustness.

## External Dependencies
- **PostgreSQL**: Primary database.
- **Font Awesome**: Icon library.
- **Bootstrap 5**: Frontend framework.
- **Flask-Login**: User session management.
- **WTForms / Flask-WTF**: Form handling and validation.
- **SQLAlchemy**: ORM for database interaction.
- **Gunicorn**: WSGI server for production deployment.
- **Werkzeug**: Password hashing.
- **Openpyxl**: Python library for server-side Excel file generation.
- **SheetJS (XLSX)**: JavaScript library for client-side Excel handling.
- **Cryptography**: Fernet symmetric encryption for SMTP credentials and sensitive data.
- **Flask-Mail**: Email sending infrastructure (integrated with multi-tenant SMTP system).