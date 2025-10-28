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
- **User Management**: Permission-based access control with over 70 granular permissions and 5 configurable standard roles. Supports advanced work schedule assignments and multi-location access.
- **Work Schedule Management**: Work schedules are company-level globals, decoupled from locations.
- **Attendance Tracking**: Features clock-in/out, break tracking, historical viewing, static QR code system, manual monthly timesheet entry with progressive saving, two-tier approval workflow (consolidation + validation), and configurable attendance types. MonthlyTimesheet tracks consolidation and validation status with distinct approval flows and role-based permissions. TimesheetReopenRequest manages requests requiring HR/Admin approval.
- **Shift Management**: Supports intelligent shift generation, recurring patterns via templates, and on-call duty management, integrated with the Mansionario system.
- **Mileage Reimbursement System**: Manages requests and calculates distances using ACI tables with manager approval workflows.
- **Data Export**: Supports CSV to Excel (.xlsx) conversion.
- **Multi-Tenant Email System**: Hybrid SMTP architecture supporting global and per-company email configurations, with encrypted SMTP passwords.
- **Password Security**: Enforces strong password requirements.
- **Platform News Management**: Dynamic content management system for a global news section, managed by SUPERADMINs.
- **Database**: Exclusively designed for PostgreSQL.

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