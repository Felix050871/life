# Life - Comprehensive Multi-Tenant SAAS Platform

## Overview
Life is a comprehensive multi-tenant SaaS workforce management platform designed to serve various companies with isolated data, custom branding, and dedicated URL paths (`/tenant/<slug>`). It integrates two main sections:

- **FLOW**: Focuses on operational team organization, shift planning, leave requests, and tracking attendance and overtime. Its purpose is to simplify work and optimize time.
- **CIRCLE**: Provides a social connection space for company updates, document sharing, and idea exchange. Its goal is to connect people and foster community within the workplace.

The platform aims to reduce bureaucracy, enhance productivity, and foster corporate community through a responsive web interface with multiple user roles and distinct permission levels.

## User Preferences
Preferred communication style: Simple, everyday language.

## Recent Changes (November 10, 2025)
- **XML Export for Validated Timesheets**: Implemented comprehensive XML export functionality for payroll integration:
  - Added `cod_giustificativo` field to AttendanceType and LeaveType models for mapping to external payroll codes
  - Created `export_validated_timesheets_xml` route in attendance blueprint
  - XML export follows standard fornitura presenze format with Dipendente/Movimenti structure
  - Uses company.code as CodAziendaUfficiale and user.matricola as CodDipendenteUfficiale
  - Matricola is synced from UserHRData.cod_si_number (7-digit formatted) via sync_operational_fields()
  - Aggregates daily hours by attendance type/leave type with cod_giustificativo mapping
  - Added Export XML button alongside Export Excel in export UI (templates/export_validated_timesheets.html)
  - Database migration executed successfully (add_xml_export_fields.sql)
  - Optimized export overlay UX: cookie-based detection closes overlay in ~2 seconds (down from 30 seconds)
- **HR as Single Source of Truth for Operational Data**: Implemented comprehensive data synchronization strategy:
  - Created `sync_operational_fields()` in `utils_hr.py` for write-through synchronization from UserHRData to User model
  - HR module (`blueprints/hr.py`) now automatically syncs operational fields (sede, work_schedule, overtime settings, aci_vehicle) to User model on save
  - UserHRData is the authoritative source; User model fields maintained for backward compatibility with existing blueprints
  - Removed operational fields from User Management UI (templates/user_management.html, templates/edit_user.html)
  - UserForm retains operational fields for compatibility with other blueprints (presidio, reperibilita, expense, attendance, holidays, shifts)
  - Added "Fornitore" contract type with nome_fornitore and partita_iva_fornitore fields to UserHRData
  - Executed database migration (add_fornitore_fields.sql) successfully
- **Previous Changes (October 31, 2025)**:
  - Critical Multi-Tenant Security Fixes in user_management.py and auth.py
  - Security Audit Completed confirming proper company_id scoping
  - Code Quality Improvements with centralized constants.py

## System Architecture

### Core Technologies
- **Backend**: Flask (Python), SQLAlchemy ORM, PostgreSQL, Flask-Login, WTForms.
- **Frontend**: Jinja2 templating, Bootstrap 5 (dark theme), custom CSS, vanilla JavaScript, Font Awesome.
- **Deployment**: Gunicorn WSGI server.

### UI/UX Decisions
The platform features a modern, responsive dark-themed Bootstrap design. It includes global Bootstrap modals, an optimized overlay system, and dynamic sidebar navigation based on user permissions. User profiles support image uploads with automatic resizing and circular display.

### System Design Choices
- **Multi-Tenant SaaS System**: Implemented with complete company isolation, path-based tenancy, and role-based administration. All core entities are scoped by `company_id`.
- **User Management**: Permission-based access control with over 70 granular permissions and 5 configurable standard roles. Supports advanced work schedule assignments and multi-location access.
- **Work Schedule Management**: Work schedules are company-level globals, decoupled from locations.
- **Attendance Tracking**: Features clock-in/out, break tracking, historical viewing, static QR code system, manual monthly timesheet entry with progressive saving, two-tier approval workflow (consolidation + validation), and configurable attendance types. MonthlyTimesheet tracks consolidation and validation status with distinct approval flows and role-based permissions. TimesheetReopenRequest manages requests requiring HR/Admin approval.
- **Leave Management**: Configurable leave types with flexible minimum duration requirements (minimum_duration_hours field), automatic seeding of default values (Ferie: 8h, Malattia: 4h), and approval workflows. Supports both requires_approval and active status flags.
- **Shift Management**: Supports intelligent shift generation, recurring patterns via templates, and on-call duty management, integrated with the Mansionario system.
- **Mileage Reimbursement System**: Manages requests and calculates distances using ACI tables with manager approval workflows.
- **Data Export**: Supports multiple export formats including Excel (.xlsx) for detailed timesheet data and XML for payroll system integration. XML export follows standard fornitura presenze format with configurable cod_giustificativo mapping for attendance and leave types.
- **Multi-Tenant Email System**: Hybrid SMTP architecture supporting global and per-company email configurations, with encrypted SMTP passwords.
- **Internal Notification System**: Centralized messaging system (`message_utils.py`) for workflow notifications. Sends internal messages to users for timesheet consolidation/validation, timesheet reopen requests (new request alerts managers, approval/rejection notifies requester), leave request approvals/rejections, and mileage reimbursement approvals/rejections. All notifications are multi-tenant isolated with proper permission-based recipient targeting.
- **Password Security**: Enforces strong password requirements.
- **Platform News Management**: Dynamic content management system for a global news section, managed by SUPERADMINs.
- **Database**: Exclusively designed for PostgreSQL. Uses db.create_all() for schema creation with automatic data seeding (seed_data.py) for default values.
- **Data Seeding**: Automatic, idempotent data seeding on application startup ensures consistent defaults across all tenants (e.g., leave type minimum durations).

### Feature Specifications
- **FLOW**: Attendance tracking, intelligent shift scheduling, leave request workflow, overtime and mileage reimbursements, time bank, on-call duty management, HR data management, project/job management (Commesse), and reports.
- **CIRCLE**: News feed and announcements, company history, groups, polls/surveys, company calendar, document management, tool links, and employee directory.
- **HR Data Management**: Comprehensive employee information system with GDPR compliance, a three-tier "Sede" architecture, and a three-section structure for contractual data, personal registry, and visits/training. Includes permission-based access, Excel export, multi-tenant isolation, and vehicle registration document uploads.
- **Mansionario System**: Centralized job title management for standardizing employee roles, with CRUD operations, active/inactive status, functional enablement flags (e.g., `abilita_turnazioni`, `abilita_reperibilita`), and multi-tenant isolation. Fully integrated with the shift system.
- **Overtime Management System**: Flexible system with "Straordinario Pagato" and "Banca Ore" types, configurable per employee.
- **Project/Job Management (Commesse)**: Complete CRUD system for managing client projects, including client tracking, categorization, date ranges, duration estimation, status tracking, optional hourly rates, and time-based resource assignments with date ranges and project manager designation. Multi-tenant isolated with permission-based access.

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