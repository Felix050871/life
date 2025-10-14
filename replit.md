# Life - Comprehensive Multi-Tenant SAAS Platform

## Overview
Life is a comprehensive multi-tenant SAAS workforce management platform consisting of two integrated sections:
- **WORKLY**: Workforce operations (attendance tracking, shift scheduling, leave management, user administration)
- **HUBLY**: Social intranet space for internal communication, collaboration, and company culture

The platform provides a responsive web interface with multiple user roles and distinct permission levels. It's designed as a **path-based multi-tenant system** serving various companies, each with isolated data, custom branding, and dedicated URL paths (`/t/<slug>`).

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Technologies
- **Backend**: Flask (Python) with SQLAlchemy ORM, PostgreSQL, Flask-Login for authentication (role-based access control), and WTForms for form handling.
- **Frontend**: Jinja2 templating, Bootstrap 5 (dark theme) with custom CSS, vanilla JavaScript for interactivity, and Font Awesome for icons. Mobile-first responsive design.
- **Deployment**: Gunicorn WSGI server.

### Platform Sections
1. **WORKLY** - Workforce Management
   - Attendance tracking with clock-in/out
   - Intelligent shift scheduling and management
   - Leave request workflow
   - Overtime and mileage reimbursements
   - Banca ore (time bank) system
   - On-call duty management (Reperibilità)
   - Reports and data export

2. **HUBLY** - Social Intranet
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
- **User Management**: Features a permission-based access control system with over 70 granular permissions (including 19 HUBLY-specific permissions) and 5 dynamically configurable standard roles. Supports advanced work schedule assignments (ORARIA vs. TURNI modes) and multi-location access. Enhanced user profiles include social fields (bio, LinkedIn, phone, department, job title) for HUBLY integration. The role management page includes a dedicated HUBLY permissions card for easy configuration of social intranet access and management capabilities.
- **Attendance Tracking**: Includes clock-in/out, break tracking, daily records, historical viewing, reporting, and a static QR code system for quick attendance marking with intelligent user status validation.
- **Shift Management**: Supports intelligent shift generation with workload balancing, recurring shift patterns via templates, and integration with leave/part-time percentages. Includes on-call duty management (`ReperibilitaShift`) and intervention tracking (`ReperibilitaIntervention`). Adheres to operational safety rules (e.g., no overlaps, 11-hour rest periods, split shifts for long durations, 24/7 coverage, weekly rest days).
- **Mileage Reimbursement System**: Manages mileage reimbursement requests, including automatic distance/amount calculation using ACI tables, multi-point routes, and a manager approval workflow.
- **UI/UX**: Modern, responsive dark-themed Bootstrap design with generic "Life" branding. Features global Bootstrap modals, an optimized overlay system, and dynamic sidebar navigation based on user permissions. Company ADMIN users (role='Amministratore', not SUPERADMIN) have dedicated "Amministrazione" dropdown in the topbar with Ruoli and Utenti links, visually separated from WORKLY/HUBLY tabs - these menus are hidden from the sidebar for a cleaner interface.
- **Data Export**: Supports CSV to Excel (.xlsx) conversion across all modules using `openpyxl` (server-side) and `SheetJS` (client-side).
- **System Logging and Optimization**: Professional logging, configuration centralization for security, performance, and maintainability.
- **Dashboard Widgets**: Dynamic widgets for team statistics, personal leave requests, shifts, on-call duties, and mileage reimbursements, controlled by user permissions.
- **Internal Messaging**: Multi-recipient internal messaging system with permission-based sending and automatic notifications for approvals/rejections.
- **User Profile Management**: Allows users to modify personal details independently, including profile image upload with automatic resizing to 200x200px, and HUBLY social fields (bio, LinkedIn URL, phone number, department, job title). Profile images are displayed in a circular format in the navbar and profile page, with a default image for users without a custom photo.
- **HUBLY Social Features**: Complete social intranet implementation with 8 core models (HublyPost, HublyGroup, HublyPoll, HublyDocument, HublyCalendarEvent, HublyComment, HublyLike, HublyToolLink) and 6 dedicated blueprints. Features include news/announcement posting with engagement (comments, likes), group management, polling system, company calendar, document repository with versioning, and customizable tool links dashboard. All HUBLY entities enforce multi-tenant isolation via company_id filtering.
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