# Life - Comprehensive Multi-Tenant SAAS Platform

## Overview
Life is a comprehensive multi-tenant SaaS workforce management platform designed to serve various companies with isolated data, custom branding, and dedicated URL paths (`/tenant/<slug>`). It integrates two main sections:

- **FLOW**: Focuses on operational team organization, shift planning, leave requests, and tracking attendance and overtime. Its purpose is to simplify work and optimize time.
- **CIRCLE**: Provides a social connection space for company updates, document sharing, and idea exchange. Its goal is to connect people and foster community within the workplace.

The platform aims to reduce bureaucracy, enhance productivity, and foster corporate community through a responsive web interface with multiple user roles and distinct permission levels.

## User Preferences
Preferred communication style: Simple, everyday language.

## Recent Updates (October 27, 2025)
**Timesheet Consolidation and Reopen Workflow**: Implemented comprehensive timesheet consolidation system with reopen request approval workflow. Once a monthly timesheet is consolidated (MonthlyTimesheet.is_consolidated), employees cannot insert, edit, or delete attendance entries for that period. Employees must submit a TimesheetReopenRequest with a reason, which requires approval from authorized personnel (HR managers, project managers with commesse permissions, or admins). Upon approval, the timesheet is reopened (is_consolidated set to False) allowing modifications. All manual entry routes (manual_entry, edit_manual_entry, delete_manual_entry) validate consolidation status before allowing operations. UI includes alert banner on attendance page when consolidated, modal for submitting reopen requests, and dedicated management page for reviewers. Multi-tenant filtering enforced on all reopen request queries. Status values follow capitalized convention: 'Pending', 'Approved', 'Rejected'.

**Previous Update (October 24, 2025)**: Completed comprehensive system-wide status value normalization from lowercase to capitalized format for all request/approval entities (LeaveRequest, OvertimeRequest, MileageRequest, ExpenseReport, ConnectionRequest, CircleGroupMembershipRequest, TimesheetReopenRequest). All status values use consistent capitalization: 'Pending', 'Approved', 'Rejected', 'Accepted'.

## System Architecture

### Core Technologies
- **Backend**: Flask (Python), SQLAlchemy ORM, PostgreSQL, Flask-Login, WTForms.
- **Frontend**: Jinja2 templating, Bootstrap 5 (dark theme), custom CSS, vanilla JavaScript, Font Awesome.
- **Deployment**: Gunicorn WSGI server.

### UI/UX Decisions
The platform features a modern, responsive dark-themed Bootstrap design. It includes global Bootstrap modals, an optimized overlay system, and dynamic sidebar navigation based on user permissions. User profiles support image uploads with automatic resizing and circular display.

### System Design Choices
- **Multi-Tenant SaaS System**: Implemented with complete company isolation, path-based tenancy, and role-based administration.
  - **Roles**: Includes a SUPERADMIN for system management and Company ADMINs for company-specific configuration.
  - **Data Isolation**: All core entities are scoped by `company_id` to ensure data separation. User credentials are unique per company. Multi-tenancy is enforced across UserRole, Reperibilità, Circle, and FLOW entities.
  - **Security**: Complete multi-tenant filtering across all blueprints and database queries.
- **User Management**: Permission-based access control with over 70 granular permissions and 5 configurable standard roles. Supports advanced work schedule assignments and multi-location access.
- **Work Schedule Management** (Updated October 24, 2025): Work schedules are now purely **company-level globals**, completely decoupled from sedi (locations). All schedules are available company-wide to all employees regardless of their operational sede. User work schedule assignment is independent from sede membership. Database schema: `WorkSchedule.sede_id` field removed entirely; unique constraint on `(company_id, name)` ensures unique schedule names per company. The `Sede` model no longer has any relationship with work schedules.
- **Attendance Tracking**: Features clock-in/out, break tracking, historical viewing, static QR code system, and manual monthly timesheet entry with progressive saving and **consolidation locking**. MonthlyTimesheet model tracks consolidation status (is_consolidated flag, consolidated_at timestamp, consolidated_by foreign key). Once consolidated, attendance entries become immutable until reopened via approval workflow. TimesheetReopenRequest model manages reopen requests with multi-tenant isolation, requiring approval from HR managers, project managers, or admins. Comprehensive timezone handling ensures all attendance timestamps are stored as naive UTC and converted to local Italian time for display and schedule validation.
- **Shift Management**: Supports intelligent shift generation, recurring patterns via templates, and on-call duty management.
- **Mileage Reimbursement System**: Manages requests and calculates distances using ACI tables with manager approval workflows.
- **Data Export**: Supports CSV to Excel (.xlsx) conversion.
- **Multi-Tenant Email System**: Hybrid SMTP architecture supporting global and per-company email configurations, with encrypted SMTP passwords.
- **Password Security**: Enforces strong password requirements with user guidance.
- **Platform News Management**: Dynamic content management system for a global news section, managed by SUPERADMINs, visible to all companies.
- **Database**: Exclusively designed for PostgreSQL.

### Feature Specifications
- **FLOW**: Attendance tracking (live and manual monthly timesheets), intelligent shift scheduling, leave request workflow, overtime and mileage reimbursements, time bank (Banca ore), on-call duty management (Reperibilità), HR data management, project/job management (Commesse), and reports.
- **CIRCLE**: News feed and announcements (posts, comments, likes, optional email notifications), company history, groups, polls/surveys, company calendar, document management, tool links, and employee directory.
- **HR Data Management**: Comprehensive employee information system with GDPR compliance. Features a `UserHRData` model for sensitive data, a three-tier "Sede" architecture distinguishing administrative, operational, and event-specific locations, and a three-section structure for contractual data, personal registry, and visits/training. Includes permission-based access, Excel export with Italian formatting, and multi-tenant isolation. Supports uploading vehicle registration documents.
- **Mansionario System** (Added October 24, 2025, fully integrated with shift system on same day): Centralized job title management system for standardizing employee roles across the organization. Replaces free-text mansione field with structured dropdown selection. Features include CRUD operations for job titles, active/inactive status toggle, functional enablement flags (abilita_turnazioni, abilita_reperibilita) to control which roles can participate in shift rotations and on-call duties, and multi-tenant isolation with company-scoped data. 
  - **Permissions**: Two-tier permission model: `can_manage_mansioni` (create/edit/delete job titles) and `can_view_mansioni` (read-only access). Menu visibility controlled via `can_access_mansioni_menu()` helper.
  - **Implementation**: Blueprint: `blueprints/mansioni.py`, Model: `Mansione` with 37 pre-populated standard job titles. Integration with HR forms via select dropdown in UserHRData.mansione field. Utility script `populate_mansioni.py` for initial data seeding across all companies.
  - **Shift Integration**: Complete migration from User.role-based to Mansionario-based shift generation. PresidioCoverage and ReperibilitaCoverage models now use `required_mansioni` field (JSON). All shift generation logic in utils.py and blueprints/shifts.py filters users by mansione with abilita_turnazioni/abilita_reperibilita flags. Multi-tenant security enforced via company_id constraints on all Mansione joins to prevent cross-tenant data leakage.
- **Overtime Management System**: Flexible system with two types: "Straordinario Pagato" (paid directly) and "Banca Ore" (accumulated in time bank). Configurable per employee with conditional UI for time bank features.
- **Project/Job Management (Commesse)** (Added October 24, 2025, enhanced October 27, 2025): Complete CRUD system for managing client projects and jobs. Features include client tracking, project categorization by activity type, date range management, optional duration estimation (hours), project status tracking (attiva/in corso/chiusa), optional hourly rate (Tariffa Oraria), **time-based resource assignments** with date ranges and project manager role designation, progress tracking with visual indicators, deadline alerts, and estimated value calculation (duration × hourly rate). Multi-tenant isolated with company-scoped filtering. 
  - **Permissions**: Two-tier permission model: `can_manage_commesse` (create/edit/delete/assign resources) and `can_view_commesse` (read-only access). Menu visibility controlled via `can_access_commesse_menu()` helper. Route-level protection via `@require_commesse_permission` decorator plus inline checks on management operations. Template-level UI gating ensures read-only users cannot see create/edit/delete actions.
  - **Resource Assignment System** (Enhanced October 27, 2025): Temporal resource assignment with period specification (data_inizio - data_fine, default to project duration), "Responsabile" (project manager) role flag with visual indicators (star badge), date constraint validation (assignments must fall within project dates), assignment status tracking (active/inactive based on current date), and dedicated helper methods for querying project managers. Model: `CommessaAssignment` with fields: user_id, commessa_id, data_inizio, data_fine, is_responsabile, assigned_at, assigned_by_id. Validation: CommessaAssignment.validate_dates() ensures temporal constraints. Helper methods: User.get_commesse_as_responsabile(), User.get_active_commesse(), User.is_responsabile_of_commessa(); Commessa.get_responsabili(), Commessa.is_responsabile(), Commessa.get_active_assignments(), Commessa.has_active_assignment().
  - **Implementation**: Blueprint: `blueprints/commesse.py`, Models: `Commessa`, `CommessaAssignment`. Helper methods in User and Commessa models follow established permission pattern.

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