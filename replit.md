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
- **Multi-Tenant System**: Fully implemented with a `Company` model, allowing each company (e.g., NS12, ATMH) to have personalized branding (logo, background image) and complete data isolation. System administrators (`is_system_admin`) manage all companies via a dedicated "System Administration" menu with full CRUD capabilities.
  - **Data Isolation**: All core entities (User, AttendanceEvent, LeaveRequest, Shift, Holiday, InternalMessage, etc.) include `company_id` foreign key
  - **Helper Utilities**: `utils_tenant.py` provides `filter_by_company()` for automatic query filtering, `set_company_on_create()` for automatic company assignment, and `get_user_company_id()` for retrieving user's company
  - **Blueprint Integration**: Leave and Attendance blueprints fully implement multi-tenant filtering; other blueprints (Shifts, Messages, Holidays) have imports ready but need query updates
  - **Migration**: All existing data migrated to default NS12 company (ID=1); admin user promoted to system admin
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