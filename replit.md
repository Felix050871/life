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
- **Multi-Tenant SaaS System**: Implemented with complete company isolation, path-based tenancy, and role-based administration.
  - **Roles**: Includes a SUPERADMIN for system management and Company ADMINs for company-specific configuration.
  - **Data Isolation**: All core entities are scoped by `company_id` to ensure data separation. User credentials are unique per company. Multi-tenancy is enforced across UserRole, Reperibilità, Circle, and FLOW entities.
  - **Security**: Complete multi-tenant filtering across all blueprints and database queries.
- **User Management**: Permission-based access control with over 70 granular permissions and 5 configurable standard roles. Supports advanced work schedule assignments and multi-location access.
- **Work Schedule Management** (Updated October 24, 2025): Work schedules are now purely **company-level globals**, completely decoupled from sedi (locations). All schedules are available company-wide to all employees regardless of their operational sede. User work schedule assignment is independent from sede membership. Database schema: `WorkSchedule.sede_id` field removed entirely; unique constraint on `(company_id, name)` ensures unique schedule names per company. The `Sede` model no longer has any relationship with work schedules.
- **Attendance Tracking**: Features clock-in/out, break tracking, historical viewing, static QR code system, and manual monthly timesheet entry with progressive saving and consolidation locking. Comprehensive timezone handling ensures all attendance timestamps are stored as naive UTC and converted to local Italian time for display and schedule validation.
- **Shift Management**: Supports intelligent shift generation, recurring patterns via templates, and on-call duty management.
- **Mileage Reimbursement System**: Manages requests and calculates distances using ACI tables with manager approval workflows.
- **Data Export**: Supports CSV to Excel (.xlsx) conversion.
- **Multi-Tenant Email System**: Hybrid SMTP architecture supporting global and per-company email configurations, with encrypted SMTP passwords.
- **Password Security**: Enforces strong password requirements with user guidance.
- **Platform News Management**: Dynamic content management system for a global news section, managed by SUPERADMINs, visible to all companies.
- **Database**: Exclusively designed for PostgreSQL.

### Feature Specifications
- **FLOW**: Attendance tracking (live and manual monthly timesheets), intelligent shift scheduling, leave request workflow, overtime and mileage reimbursements, time bank (Banca ore), on-call duty management (Reperibilità), HR data management, and reports.
- **CIRCLE**: News feed and announcements (posts, comments, likes, optional email notifications), company history, groups, polls/surveys, company calendar, document management, tool links, and employee directory.
- **HR Data Management**: Comprehensive employee information system with GDPR compliance. Features a `UserHRData` model for sensitive data, a three-tier "Sede" architecture distinguishing administrative, operational, and event-specific locations, and a three-section structure for contractual data, personal registry, and visits/training. Includes permission-based access, Excel export with Italian formatting, and multi-tenant isolation. Supports uploading vehicle registration documents.
- **Overtime Management System**: Flexible system with two types: "Straordinario Pagato" (paid directly) and "Banca Ore" (accumulated in time bank). Configurable per employee with conditional UI for time bank features.

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