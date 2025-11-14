# Life - Comprehensive Multi-Tenant SAAS Platform

## Overview
Life is a comprehensive multi-tenant SaaS workforce management platform designed for various companies, offering isolated data, custom branding, and dedicated URL paths (`/tenant/<slug>`). It comprises two main sections:

- **FLOW**: Manages operational team organization, shift planning, leave requests, attendance, and overtime, aiming to simplify work and optimize time.
- **CIRCLE**: Provides a social platform for company updates, document sharing, and idea exchange, fostering community within the workplace.

The platform's goal is to reduce bureaucracy, enhance productivity, and build corporate community through a responsive web interface with multiple user roles and distinct permission levels.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### UI/UX Decisions
The platform utilizes a modern, responsive dark-themed Bootstrap design with global modals, an optimized overlay system, and dynamic sidebar navigation based on user permissions. User profiles support image uploads with automatic resizing.

### System Design Choices
- **Multi-Tenant SaaS System**: Complete company isolation with path-based tenancy and role-based administration. All core entities are scoped by `company_id`.
- **User Management**: Permission-based access control with over 70 granular permissions and 5 configurable standard roles, supporting advanced work schedule assignments and multi-location access.
- **Work Schedule Management**: Company-level global work schedules, decoupled from locations.
- **Attendance Tracking**: Features clock-in/out, break tracking, historical viewing, static QR code system, manual monthly timesheet entry with two-tier approval, and configurable attendance types. Includes weekly contractual hours enforcement and dynamic end time calculation.
- **Leave Management**: Configurable leave types with approval workflows. Includes an automated leave accrual tracking system (vacation days/permit hours) with on-demand balance calculation, part-time adjustments, and unit toggling (hours/days) for vacation accrual. An interactive calendar view (FullCalendar.js) displays leave and shift information. **Flexible weekend/holiday counting** via `count_weekends_holidays` flag per leave type: enables proper distinction between leave types that include weekends/holidays (e.g., vacation) vs. those that count only working days (e.g., sick leave), with automatic exclusion of Saturdays, Sundays, and company/sede holidays.
- **Shift Management**: Intelligent shift generation, recurring patterns via templates, and on-call duty management.
- **Mileage Reimbursement System**: Manages requests and calculates distances using ACI tables with manager approval.
- **Data Export**: Supports Excel (.xlsx) for timesheets and XML for payroll system integration.
- **Multi-Tenant Email System**: Hybrid SMTP architecture with global and per-company configurations.
- **Internal Notification System**: Centralized, multi-tenant isolated messaging for workflow notifications.
- **Session Management System**: Database-backed user session tracking with inactivity timeouts and concurrent session limiting (max 2 sessions) with FIFO invalidation.
- **Platform News Management**: Dynamic content management for a global news section.
- **Database**: Exclusively PostgreSQL, with idempotent data seeding.
- **CIRCLE Module**: Includes a dynamic news feed, channel-based communications, groups, polls, company calendar, document management, tool links, and employee directory.
- **HR Data Management**: Comprehensive employee information system with GDPR compliance, a three-tier "Sede" architecture, and sections for contractual, personal, and training data. Features include contract history tracking with versioning and temporal validity, and a secondment management system for tracking employee placements.
- **Mansionario System**: Centralized job title management for standardizing employee roles, integrated with the shift system.
- **Overtime Management System**: Flexible system with "Straordinario Pagato" and "Banca Ore" types, configurable per employee.
- **Project/Job Management (Commesse)**: CRUD system for managing client projects, including client tracking, categorization, and resource assignments.
- **Social Safety Net System (Ammortizzatori Sociali)**: Manages Italian workforce reduction programs with program creation, employee assignments, and automatic weekly hour reduction enforcement, integrated with attendance and contract history.
- **CCNL Structured Data System**: Hierarchical three-tier management system for Italian national collective labor agreements (CCNL → Qualification → Level) with multi-tenant isolation, migration strategy, and JSON API endpoints.

### Core Technologies
- **Backend**: Flask (Python), SQLAlchemy ORM, PostgreSQL.
- **Frontend**: Jinja2 templating, Bootstrap 5, custom CSS, vanilla JavaScript.
- **Deployment**: Gunicorn WSGI server.

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
- **FullCalendar.js**: Interactive calendar component.