# Life - Comprehensive Multi-Tenant SAAS Platform

## Overview
Life is a comprehensive multi-tenant SaaS workforce management platform, designed as a path-based multi-tenant system to serve various companies with isolated data, custom branding, and dedicated URL paths (`/tenant/<slug>`). It consists of two integrated sections:

- **FLOW**: "Il tuo gestore smart del tempo" - Focuses on operational team organization, shift planning, leave requests, and tracking attendance and overtime. *Tagline: Semplifica il lavoro, moltiplica il tempo. ⏱️*
- **CIRCLE**: "Il centro della tua community aziendale" - Provides a social connection space for company updates, quick access to documents and tools, and idea sharing among colleagues. *Tagline: Connettiti alle persone, connettiti al lavoro. 🤝*

The platform aims to reduce bureaucracy, enhance productivity, and foster corporate community, offering a responsive web interface with multiple user roles and distinct permission levels.

## User Preferences
Preferred communication style: Simple, everyday language.

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
  - **Security**: Complete multi-tenant filtering across all blueprints and database queries.
- **User Management**: A permission-based access control system with over 70 granular permissions and 5 configurable standard roles. Supports advanced work schedule assignments and multi-location access. Enhanced user profiles include social fields for CIRCLE integration.
- **Attendance Tracking**: Includes clock-in/out, break tracking, historical viewing, and a static QR code system for attendance marking.
- **Shift Management**: Supports intelligent shift generation, recurring shift patterns via templates, and on-call duty management, adhering to operational safety rules.
- **Mileage Reimbursement System**: Manages requests, calculates distances using ACI tables, and incorporates a manager approval workflow.
- **Data Export**: Supports CSV to Excel (.xlsx) conversion using `openpyxl` (server-side) and `SheetJS` (client-side).
- **Multi-Tenant Email System**: Hybrid SMTP architecture supporting both global (SUPERADMIN) and per-company email configurations. SMTP passwords are encrypted at rest using Fernet encryption. Company ADMINs can configure and test SMTP settings via a dedicated UI.
- **Password Security**: Enhanced password validation enforces strong password requirements (minimum 8 characters with uppercase, lowercase, number, and special character) across all authentication flows, with user guidance in templates.
- **Platform News Management**: A dynamic content management system for a global news section on the home page, exclusively managed by SUPERADMINs. News items are system-level, visible to all companies, and feature customizable icons, colors, and ordering.
- **Database**: Exclusively designed for PostgreSQL for robustness.

### Feature Specifications
- **FLOW**: Attendance tracking, intelligent shift scheduling, leave request workflow, overtime and mileage reimbursements, time bank (Banca ore), on-call duty management (Reperibilità), and reports.
- **CIRCLE**: News feed and announcements (posts with comments/likes, optional email notifications), company history (Delorean), groups, polls and surveys, company calendar, document management, tool links, and employee directory (Personas).
  - **Email Notifications for Announcements**: Option to send email notifications to all active company users for "comunicazione" posts, utilizing the multi-tenant email system.

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