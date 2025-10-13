# Life - Workforce Management Platform

## Overview
Life is a comprehensive workforce management platform for employee attendance tracking, shift scheduling, leave management, and user administration. It provides a responsive web interface and supports multiple user roles with distinct permission levels. The project aims to be a standalone, adaptable solution for any organization, offering intelligent shift generation, detailed attendance recording, and a robust user management system with granular access controls. It is designed as a multi-tenant system to serve various companies, each with isolated data and branding.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Technologies
- **Backend**: Flask (Python) with SQLAlchemy ORM, PostgreSQL, Flask-Login for authentication (role-based access control), and WTForms for form handling.
- **Frontend**: Jinja2 templating, Bootstrap 5 (dark theme) with custom CSS, vanilla JavaScript for interactivity, and Font Awesome for icons. Mobile-first responsive design.
- **Deployment**: Gunicorn WSGI server.

### Key Architectural Decisions & Features
- **Multi-Tenant SaaS System**: Fully implemented as a Software-as-a-Service platform with complete company isolation and role-based administration.
  - **SUPERADMIN Role**: System-level administrators (`is_system_admin=true`, `company_id=null`) manage the entire SaaS platform
    - Create and manage companies via "Amministrazione Sistema" menu
    - Mandatory creation of company ADMIN during company setup (transactional workflow)
    - Cannot access company-specific operational data (sedi, users, shifts, etc.)
  - **Company ADMIN Role**: Each company has its own administrator (`role='Amministratore'`, linked to specific `company_id`)
    - Full control over their company's configuration (sedi, users, mail settings, etc.)
    - Cannot access other companies' data or create new companies
    - Auto-assigned `all_sedi=true` for full location access within their company
  - **Data Isolation**: All core entities (User, AttendanceEvent, LeaveRequest, Shift, Holiday, InternalMessage, etc.) include `company_id` foreign key
  - **Helper Utilities**: `utils_tenant.py` provides `filter_by_company()` for automatic query filtering, `set_company_on_create()` for automatic company assignment, and `get_user_company_id()` for retrieving user's company
  - **Blueprint Integration**: Leave and Attendance blueprints fully implement multi-tenant filtering; other blueprints (Shifts, Messages, Holidays, User Management) need complete company-scoped filtering
  - **Company Creation Workflow**: SUPERADMIN creates company with mandatory admin user in single transaction; validates unique codes, usernames, and emails
- **User Management**: Features a permission-based access control system with over 30 granular permissions and 5 dynamically configurable standard roles. Supports advanced work schedule assignments (ORARIA vs. TURNI modes) and multi-location access.
- **Attendance Tracking**: Includes clock-in/out, break tracking, daily records, historical viewing, reporting, and a static QR code system for quick attendance marking with intelligent user status validation.
- **Shift Management**: Supports intelligent shift generation with workload balancing, recurring shift patterns via templates, and integration with leave/part-time percentages. Includes on-call duty management (`ReperibilitaShift`) and intervention tracking (`ReperibilitaIntervention`). Adheres to operational safety rules (e.g., no overlaps, 11-hour rest periods, split shifts for long durations, 24/7 coverage, weekly rest days).
- **Mileage Reimbursement System**: Manages mileage reimbursement requests, including automatic distance/amount calculation using ACI tables, multi-point routes, and a manager approval workflow.
- **UI/UX**: Modern, responsive dark-themed Bootstrap design with generic "Life" branding. Features global Bootstrap modals, an optimized overlay system, and dynamic sidebar navigation based on user permissions.
- **Data Export**: Supports CSV to Excel (.xlsx) conversion across all modules using `openpyxl` (server-side) and `SheetJS` (client-side).
- **System Logging and Optimization**: Professional logging, configuration centralization for security, performance, and maintainability.
- **Dashboard Widgets**: Dynamic widgets for team statistics, personal leave requests, shifts, on-call duties, and mileage reimbursements, controlled by user permissions.
- **Internal Messaging**: Multi-recipient internal messaging system with permission-based sending and automatic notifications for approvals/rejections.
- **User Profile Management**: Allows users to modify personal details independently.
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