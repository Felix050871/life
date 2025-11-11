# Life - Comprehensive Multi-Tenant SAAS Platform

## Overview
Life is a comprehensive multi-tenant SaaS workforce management platform designed to serve various companies with isolated data, custom branding, and dedicated URL paths (`/tenant/<slug>`). It integrates two main sections:

- **FLOW**: Focuses on operational team organization, shift planning, leave requests, and tracking attendance and overtime. Its purpose is to simplify work and optimize time.
- **CIRCLE**: Provides a social connection space for company updates, document sharing, and idea exchange. Its goal is to connect people and foster community within the workplace.

The platform aims to reduce bureaucracy, enhance productivity, and foster corporate community through a responsive web interface with multiple user roles and distinct permission levels.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Technologies
- **Backend**: Flask (Python), SQLAlchemy ORM, PostgreSQL, Flask-Login, WTForms.
- **Frontend**: Jinja2 templating, Bootstrap 5 (dark theme), custom CSS, vanilla JavaScript, Font Awesome.
- **Deployment**: Gunicorn WSGI server.

### UI/UX Decisions
The platform features a modern, responsive dark-themed Bootstrap design. It includes global Bootstrap modals, an optimized overlay system, and dynamic sidebar navigation based on user permissions. User profiles support image uploads with automatic resizing and circular display.

### System Design Choices
- **Multi-Tenant SaaS System**: Implemented with complete company isolation, path-based tenancy, and role-based administration. All core entities are scoped by `company_id`.
- **User Management**: Permission-based access control with over 70 granular permissions and 5 configurable standard roles. Supports advanced work schedule assignments and multi-location access. HR data is the single source of truth, synchronizing operational fields to the User model.
- **Work Schedule Management**: Work schedules are company-level globals, decoupled from locations.
- **Attendance Tracking**: Features clock-in/out, break tracking, historical viewing, static QR code system, manual monthly timesheet entry with progressive saving, two-tier approval workflow (consolidation + validation), and configurable attendance types. MonthlyTimesheet tracks consolidation and validation status with distinct approval flows and role-based permissions. Includes timesheet compilation deadline enforcement with an unlock request workflow. **NEW: Weekly Contractual Hours Enforcement** - Intelligent distribution of weekly hours based on active contract (e.g., 39h/week → Mon-Thu 8h, Fri 7h) with automatic bulk fill using ISO week boundaries, per-week state tracking for partial weeks and mid-month contract changes, dynamic end time calculation (start + daily hours + break), and manual entry validation blocking submissions exceeding weekly limits with detailed error messages.
- **Leave Management**: Configurable leave types with flexible minimum duration requirements and approval workflows. **NEW: Leave Accrual Tracking System** - Automated calculation of vacation days and permit hours based on monthly accrual rates configured in HR data. Features on-demand balance calculation (accrued vs. used), part-time adjustment, user-facing balance views, and manager overview with Excel export. Accrual rates stored as NUMERIC(10,2) in `gg_ferie_maturate_mese` (days/month) and `hh_permesso_maturate_mese` (hours/month) fields. **NEW: Interactive Calendar View** - Full-featured calendar interface powered by FullCalendar.js displaying approved leaves (green), pending requests (yellow), rejected/cancelled requests (red/gray), and work shifts (blue). Features view modes (personal/company-wide), location-based filtering, event type toggles, multi-view support (month/week/day/list), and detailed event modals with quick navigation to related sections.
- **Shift Management**: Supports intelligent shift generation, recurring patterns via templates, and on-call duty management, integrated with the Mansionario system.
- **Mileage Reimbursement System**: Manages requests and calculates distances using ACI tables with manager approval workflows.
- **Data Export**: Supports multiple export formats including Excel (.xlsx) for detailed timesheet data and XML for payroll system integration (standard fornitura presenze format with configurable `cod_giustificativo` mapping).
- **Multi-Tenant Email System**: Hybrid SMTP architecture supporting global and per-company email configurations, with encrypted SMTP passwords.
- **Internal Notification System**: Centralized messaging system for workflow notifications, multi-tenant isolated with permission-based recipient targeting.
- **Password Security**: Enforces strong password requirements.
- **Platform News Management**: Dynamic content management system for a global news section, managed by SUPERADMINs.
- **Database**: Exclusively designed for PostgreSQL, with automatic, idempotent data seeding for default values.
- **CIRCLE Module**: Features include a dynamic news feed, channel-based communications (with Quill editor integration), groups (decoupled from channels), polls, company calendar, document management, tool links, and employee directory.
- **HR Data Management**: Comprehensive employee information system with GDPR compliance, a three-tier "Sede" architecture, and a three-section structure for contractual data, personal registry, and visits/training. Includes permission-based access, Excel export, multi-tenant isolation, and vehicle registration document uploads. **NEW: Contract History Tracking System** - Comprehensive versioning system tracking all 37 contractual, economic, and operational fields with automatic snapshot creation on changes, temporal validity (effective_from/to dates), visual change highlighting in timeline view, date filtering, pagination, and Excel export. Snapshots sourced from ContractHistory for point-in-time accuracy.
- **Mansionario System**: Centralized job title management for standardizing employee roles, with CRUD operations, functional enablement flags, and multi-tenant isolation, fully integrated with the shift system.
- **Overtime Management System**: Flexible system with "Straordinario Pagato" and "Banca Ore" types, configurable per employee.
- **Project/Job Management (Commesse)**: Complete CRUD system for managing client projects, including client tracking, categorization, date ranges, duration estimation, status tracking, optional hourly rates, and time-based resource assignments.

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
- **FullCalendar.js**: Interactive calendar component for visualizing leaves and shifts.