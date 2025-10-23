# Life - Comprehensive Multi-Tenant SAAS Platform

## Overview
Life is a comprehensive multi-tenant SaaS workforce management platform, designed as a path-based multi-tenant system to serve various companies with isolated data, custom branding, and dedicated URL paths (`/tenant/<slug>`). It consists of two integrated sections:

- **FLOW**: "Il tuo gestore smart del tempo" - Focuses on operational team organization, shift planning, leave requests, and tracking attendance and overtime. *Tagline: Semplifica il lavoro, moltiplica il tempo. ⏱️*
- **CIRCLE**: "Il centro della tua community aziendale" - Provides a social connection space for company updates, quick access to documents and tools, and idea sharing among colleagues. *Tagline: Connettiti alle persone, connettiti al lavoro. 🤝*

The platform aims to reduce bureaucracy, enhance productivity, and foster corporate community, offering a responsive web interface with multiple user roles and distinct permission levels.

## User Preferences
Preferred communication style: Simple, everyday language.

## Recent Bug Fixes (October 2025)

### Critical Multi-Tenant Fixes
- **User.get_role_obj() Bug**: Fixed method to use explicit `company_id` filtering instead of `filter_by_company()` context-based lookup. Previously, the method could return roles from wrong companies, causing incorrect permission checks.
- **Dashboard all_sedi Logic Bug**: Corrected role-based filtering in dashboard widgets. Previously, Responsabile/Management users with `all_sedi=True` were incorrectly filtered to only their sede because role check happened before `all_sedi` check. Now properly checks `all_sedi` first for all roles.
- **Attendance Dashboard Permission Fix**: Changed attendance status display condition from `can_view_attendance()` to `can_view_my_attendance() OR can_view_attendance()` to support Operatore role viewing their own presence data.
- **Timezone Architecture & Complete Fix (October 22, 2025)**: Implemented comprehensive timezone handling for attendance timestamps with automatic UTC normalization.
  - **Root Cause**: `AttendanceEvent.timestamp` column is `db.DateTime` (naive, without timezone). SQLAlchemy automatically converts timezone-aware datetimes to UTC before stripping timezone info, creating a naive UTC storage pattern.
  - **Solution**:
    1. **SQLAlchemy Event Listener**: Added `normalize_attendance_timestamp` listener in models.py that automatically converts ANY timezone-aware datetime to naive UTC before saving, ensuring consistent UTC storage.
    2. **Display Conversion**: Created `timestamp_italian` property on AttendanceEvent model that converts naive UTC timestamps to Italian time (UTC+1/+2) for display.
    3. **Schedule Checking**: Updated `check_user_schedule_with_permissions()` in utils.py to correctly interpret naive timestamps as UTC before converting to Italian time for comparisons with work schedules.
  - **Files Updated**: 
    - models.py (event listener + timestamp_italian property)
    - templates/dashboard.html, templates/attendance.html, templates/dashboard_team.html (all use timestamp_italian)
    - utils.py (schedule checking with UTC→Italian conversion)
    - blueprints/attendance.py (export CSV/Excel, JSON responses, flash messages)
    - blueprints/dashboard.py (PDF export)
    - blueprints/qr.py (API JSON responses)
  - **Architecture**: All AttendanceEvent timestamps are ALWAYS stored as naive UTC in PostgreSQL. Conversion to Italian time happens only at display (via `timestamp_italian` property) and during schedule validation (via utils.py conversion).
  - **Impact**: All attendance event times display correctly in Italian time across dashboard, attendance pages, team views, exports (CSV/Excel/PDF), API responses, and all schedule indicators (anticipo/ritardo/straordinario) work correctly.
  - **Data Migration**: Fixed 466 records with date mismatch, 48 manual timestamps, and removed 116 duplicate/batch events to ensure data consistency.

## System Architecture

### Core Technologies
- **Backend**: Flask (Python), SQLAlchemy ORM, PostgreSQL, Flask-Login for authentication, WTForms.
- **Frontend**: Jinja2 templating, Bootstrap 5 (dark theme), custom CSS, vanilla JavaScript, Font Awesome.
- **Deployment**: Gunicorn WSGI server.

### UI/UX Decisions
The platform features a modern, responsive dark-themed Bootstrap design with generic "Life" branding. It includes global Bootstrap modals, an optimized overlay system, and dynamic sidebar navigation based on user permissions. User profiles support image uploads with automatic resizing and display in a circular format.

### System Design Choices
- **Multi-Tenant SaaS System**: Implemented with complete company isolation, path-based tenancy (`/tenant/<slug>`), and role-based administration.
  - **Roles**: Features a SUPERADMIN role for system-level management (creating companies) and Company ADMIN roles for company-specific configuration and user management.
  - **Data Isolation**: All core entities are scoped by `company_id` to ensure data separation. User credentials (username, email) are unique per company.
    - **UserRole Multi-Tenancy** (October 2025): UserRole table now has `company_id` with unique constraint `(name, company_id)` instead of just `name`. Each company has its own set of roles with the same names but different permissions and configurations. All UserRole queries use `filter_by_company()` for proper tenant isolation.
    - **Reperibilità Multi-Tenancy** (October 2025): ReperibilitaCoverage, ReperibilitaShift, and ReperibilitaIntervention tables now have `company_id` for complete isolation of on-call duty data. All 9 files with reperibilità queries updated to use `filter_by_company()`.
    - **Circle/Hubly Multi-Tenancy** (October 2025): All Circle entities (CirclePost, CirclePoll, CircleGroup, CircleDocument, CircleCalendarEvent, CircleToolLink) have `company_id`. Dependent entities (CircleComment, CircleLike, CircleGroupPost) isolated via foreign key relationships. All 7 Circle blueprints verified and updated to use `filter_by_company()` for complete tenant isolation.
    - **FLOW Multi-Tenancy** (October 2025): All 12 FLOW entities (AttendanceEvent, Shift, ShiftTemplate, LeaveRequest, LeaveType, OvertimeRequest, MileageRequest, OvertimeType, Sede, WorkSchedule, PresidioCoverageTemplate, PresidioCoverage) have `company_id` for complete isolation. All blueprints (attendance, leave, expense, admin, banca_ore, qr, api) verified and updated to use `filter_by_company()`. ACITable correctly remains global as reference table.
  - **Security**: Complete multi-tenant filtering across all blueprints and database queries using `filter_by_company()` and `set_company_on_create()` utilities.
- **User Management**: A permission-based access control system with over 70 granular permissions and 5 configurable standard roles. Supports advanced work schedule assignments and multi-location access. Enhanced user profiles include social fields for CIRCLE integration.
- **Attendance Tracking**: Includes clock-in/out, break tracking, historical viewing, and a static QR code system for attendance marking. Features **manual monthly timesheet** entry allowing users to insert attendance data retrospectively with progressive saving, consolidation locking, and clear visual distinction between manually-entered and live-recorded data.
- **Shift Management**: Supports intelligent shift generation, recurring shift patterns via templates, and on-call duty management, adhering to operational safety rules.
- **Mileage Reimbursement System**: Manages requests, calculates distances using ACI tables, and incorporates a manager approval workflow.
- **Data Export**: Supports CSV to Excel (.xlsx) conversion using `openpyxl` (server-side) and `SheetJS` (client-side).
- **Multi-Tenant Email System**: Hybrid SMTP architecture supporting both global (SUPERADMIN) and per-company email configurations. SMTP passwords are encrypted at rest using Fernet encryption. Company ADMINs can configure and test SMTP settings via a dedicated UI.
- **Password Security**: Enhanced password validation enforces strong password requirements (minimum 8 characters with uppercase, lowercase, number, and special character) across all authentication flows, with user guidance in templates.
- **Platform News Management**: A dynamic content management system for a global news section on the home page, exclusively managed by SUPERADMINs. News items are system-level, visible to all companies, and feature customizable icons, colors, and ordering.
- **Database**: Exclusively designed for PostgreSQL for robustness.

### Feature Specifications
- **FLOW**: Attendance tracking (live and manual monthly timesheets), intelligent shift scheduling, leave request workflow, overtime and mileage reimbursements, time bank (Banca ore), on-call duty management (Reperibilità), HR data management, and reports.
- **CIRCLE**: News feed and announcements (posts with comments/likes, optional email notifications), company history (Delorean), groups, polls and surveys, company calendar, document management, tool links, and employee directory (Personas).
  - **Email Notifications for Announcements**: Option to send email notifications to all active company users for "comunicazione" posts, utilizing the multi-tenant email system.
- **HR Data Management (October 2025)**: Comprehensive employee information system with sensitive data protection, featuring:
  - **UserHRData Model**: Separate table with 1-to-1 relationship to User for GDPR compliance and security isolation
  - **Employee Fields**: Matricola (employee ID), codice fiscale (tax code), birth data (date, city, province), complete address (via, CAP, city, province), contract details (type, start/end dates, hours/week, CCNL), economic data (RAL, base salary, meal vouchers, fuel card), bank details (IBAN), emergency contacts, and document management (ID card, driver's license, passport)
  - **Permission-Based Access**: Three-tier permission system (can_manage_hr_data for full edit, can_view_hr_data for read-only company-wide access, can_view_my_hr_data for personal data viewing)
  - **Excel Export**: Single-click export of complete employee database in Excel format with Italian formatting
  - **Multi-Tenant Isolation**: All HR data properly scoped by company_id with filter_by_company() throughout
  - **UI/UX**: Bootstrap-styled templates (hr_list.html for employee directory, hr_detail.html for individual record editing) with sidebar menu integration

## External Dependencies
- **PostgreSQL**: Primary database.
- **Font Awesome**: Icon library.
- **Bootstrap 5**: Frontend framework.
- **Flask-Login**: User session management.
- **WTForms / Flask-WTF**: Form handling and validation.
- **SQLAlchemy**: ORM for database interaction.
- **Gunicorn**: WSGI server.
- **Werkzeug**: Password hashing.
- **Openpyxl**: Server-side Excel file generation.
- **SheetJS (XLSX)**: Client-side Excel handling.
- **Cryptography**: Fernet symmetric encryption.
- **Flask-Mail**: Email sending infrastructure.