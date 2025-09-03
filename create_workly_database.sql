Processing: user_role
Processing: sede
Processing: work_schedule
Processing: aci_table
Processing: user
Processing: user_sede_association
Processing: leave_type
Processing: leave_request
Processing: attendance_event
Processing: shift_template
Processing: shift
Processing: presidio_coverage_template
Processing: presidio_coverage
Processing: reperibilita_template
Processing: reperibilita_coverage
Processing: reperibilita_shift
Processing: intervention
Processing: reperibilita_intervention
Processing: holiday
Processing: password_reset_token
Processing: expense_category
Processing: expense_report
Processing: overtime_type
Processing: overtime_request
Processing: mileage_request
Processing: internal_message
-- ============================================
-- WORKLY DATABASE CREATION SCRIPT
-- Complete schema recreation script
-- Generated from current database structure
-- ============================================

-- Drop database if exists and create new
-- DROP DATABASE IF EXISTS workly;
-- CREATE DATABASE workly;
-- \c workly;

-- Set timezone
SET timezone = 'Europe/Rome';


-- Table: user_role
CREATE TABLE public.user_role (id integer NOT NULL DEFAULT nextval('user_role_id_seq'::regclass), name character varying(50) NOT NULL, display_name character varying(100) NOT NULL, description text, permissions json, active boolean, created_at timestamp without time zone);


-- Table: sede
CREATE TABLE public.sede (id integer NOT NULL DEFAULT nextval('sede_id_seq'::regclass), name character varying(100) NOT NULL, address character varying(200), description text, tipologia character varying(20) NOT NULL, active boolean NOT NULL, created_at timestamp without time zone);


-- Table: work_schedule
CREATE TABLE public.work_schedule (id integer NOT NULL DEFAULT nextval('work_schedule_id_seq'::regclass), sede_id integer NOT NULL, name character varying(100) NOT NULL, start_time_min time without time zone NOT NULL, start_time_max time without time zone NOT NULL, end_time_min time without time zone NOT NULL, end_time_max time without time zone NOT NULL, start_time time without time zone, end_time time without time zone, days_of_week json NOT NULL, description text, active boolean NOT NULL, created_at timestamp without time zone);


-- Table: aci_table
CREATE TABLE public.aci_table (id integer NOT NULL DEFAULT nextval('aci_table_id_seq'::regclass), tipologia character varying(100) NOT NULL, marca character varying(100) NOT NULL, modello character varying(200) NOT NULL, costo_km numeric(10,4) NOT NULL, created_at timestamp without time zone, updated_at timestamp without time zone);


-- Table: user
CREATE TABLE public."user" (id integer NOT NULL DEFAULT nextval('user_id_seq'::regclass), username character varying(80) NOT NULL, email character varying(120) NOT NULL, password_hash character varying(256) NOT NULL, role character varying(50) NOT NULL, first_name character varying(100) NOT NULL, last_name character varying(100) NOT NULL, sede_id integer, all_sedi boolean, work_schedule_id integer, aci_vehicle_id integer, active boolean, part_time_percentage double precision, created_at timestamp without time zone);


-- Table: user_sede_association
CREATE TABLE public.user_sede_association (user_id integer NOT NULL, sede_id integer NOT NULL);


-- Table: leave_type
CREATE TABLE public.leave_type (id integer NOT NULL DEFAULT nextval('leave_type_id_seq'::regclass), name character varying(100) NOT NULL, description text, requires_approval boolean, active boolean, created_at timestamp without time zone, updated_at timestamp without time zone);


-- Table: leave_request
CREATE TABLE public.leave_request (id integer NOT NULL DEFAULT nextval('leave_request_id_seq'::regclass), user_id integer NOT NULL, leave_type_id integer, start_date date NOT NULL, end_date date NOT NULL, leave_type character varying(50), reason text, status character varying(20), approved_by integer, approved_at timestamp without time zone, created_at timestamp without time zone, start_time time without time zone, end_time time without time zone);


-- Table: attendance_event
CREATE TABLE public.attendance_event (id integer NOT NULL DEFAULT nextval('attendance_event_id_seq'::regclass), user_id integer NOT NULL, date date NOT NULL, event_type character varying(20) NOT NULL, "timestamp" timestamp without time zone NOT NULL, sede_id integer, notes text, shift_status character varying(20), created_at timestamp without time zone);


-- Table: shift_template
CREATE TABLE public.shift_template (id integer NOT NULL DEFAULT nextval('shift_template_id_seq'::regclass), name character varying(100) NOT NULL, start_date date NOT NULL, end_date date NOT NULL, description text, created_by integer NOT NULL, created_at timestamp without time zone);


-- Table: shift
CREATE TABLE public.shift (id integer NOT NULL DEFAULT nextval('shift_id_seq'::regclass), user_id integer NOT NULL, date date NOT NULL, start_time time without time zone NOT NULL, end_time time without time zone NOT NULL, shift_type character varying(50) NOT NULL, created_at timestamp without time zone, created_by integer NOT NULL);


-- Table: presidio_coverage_template
CREATE TABLE public.presidio_coverage_template (id integer NOT NULL DEFAULT nextval('presidio_coverage_template_id_seq'::regclass), name character varying(100) NOT NULL, start_date date NOT NULL, end_date date NOT NULL, description character varying(200), sede_id integer, active boolean, created_by integer NOT NULL, created_at timestamp without time zone, updated_at timestamp without time zone);


-- Table: presidio_coverage
CREATE TABLE public.presidio_coverage (id integer NOT NULL DEFAULT nextval('presidio_coverage_id_seq'::regclass), template_id integer, day_of_week integer NOT NULL, start_time time without time zone NOT NULL, end_time time without time zone NOT NULL, required_roles text NOT NULL, role_count integer, break_start time without time zone, break_end time without time zone, description character varying(200), active boolean, start_date date, end_date date, created_by integer NOT NULL, created_at timestamp without time zone);


-- Table: reperibilita_template
CREATE TABLE public.reperibilita_template (id integer NOT NULL DEFAULT nextval('reperibilita_template_id_seq'::regclass), name character varying(100) NOT NULL, start_date date NOT NULL, end_date date NOT NULL, description text, created_by integer NOT NULL, created_at timestamp without time zone);


-- Table: reperibilita_coverage
CREATE TABLE public.reperibilita_coverage (id integer NOT NULL DEFAULT nextval('reperibilita_coverage_id_seq'::regclass), day_of_week integer NOT NULL, start_time time without time zone NOT NULL, end_time time without time zone NOT NULL, required_roles text NOT NULL, sedi_ids text NOT NULL, description character varying(200), active boolean, start_date date NOT NULL, end_date date NOT NULL, created_by integer NOT NULL, created_at timestamp without time zone);


-- Table: reperibilita_shift
CREATE TABLE public.reperibilita_shift (id integer NOT NULL DEFAULT nextval('reperibilita_shift_id_seq'::regclass), user_id integer NOT NULL, date date NOT NULL, start_time time without time zone NOT NULL, end_time time without time zone NOT NULL, description character varying(200), created_at timestamp without time zone, created_by integer NOT NULL);


-- Table: intervention
CREATE TABLE public.intervention (id integer NOT NULL DEFAULT nextval('intervention_id_seq'::regclass), user_id integer NOT NULL, start_datetime timestamp without time zone NOT NULL, end_datetime timestamp without time zone, description text, priority character varying(10) NOT NULL, is_remote boolean NOT NULL, created_at timestamp without time zone);


-- Table: reperibilita_intervention
CREATE TABLE public.reperibilita_intervention (id integer NOT NULL DEFAULT nextval('reperibilita_intervention_id_seq'::regclass), user_id integer NOT NULL, shift_id integer, start_datetime timestamp without time zone NOT NULL, end_datetime timestamp without time zone, description text, priority character varying(10) NOT NULL, is_remote boolean NOT NULL, created_at timestamp without time zone);


-- Table: holiday
CREATE TABLE public.holiday (id integer NOT NULL DEFAULT nextval('holiday_id_seq'::regclass), name character varying(100) NOT NULL, month integer NOT NULL, day integer NOT NULL, sede_id integer, active boolean NOT NULL, description character varying(200), created_at timestamp without time zone, created_by integer NOT NULL);


-- Table: password_reset_token
CREATE TABLE public.password_reset_token (id integer NOT NULL DEFAULT nextval('password_reset_token_id_seq'::regclass), user_id integer NOT NULL, token character varying(100) NOT NULL, expires_at timestamp without time zone NOT NULL, used boolean NOT NULL, created_at timestamp without time zone);


-- Table: expense_category
CREATE TABLE public.expense_category (id integer NOT NULL DEFAULT nextval('expense_category_id_seq'::regclass), name character varying(100) NOT NULL, description character varying(255), active boolean, created_at timestamp without time zone, created_by integer NOT NULL);


-- Table: expense_report
CREATE TABLE public.expense_report (id integer NOT NULL DEFAULT nextval('expense_report_id_seq'::regclass), employee_id integer NOT NULL, expense_date date NOT NULL, description text NOT NULL, amount numeric(10,2) NOT NULL, category_id integer NOT NULL, receipt_filename character varying(255), status character varying(20) NOT NULL, approved_by integer, approved_at timestamp without time zone, approval_comment text, created_at timestamp without time zone, updated_at timestamp without time zone);


-- Table: overtime_type
CREATE TABLE public.overtime_type (id integer NOT NULL DEFAULT nextval('overtime_type_id_seq'::regclass), name character varying(100) NOT NULL, description text, hourly_rate_multiplier double precision, active boolean, created_at timestamp without time zone);


-- Table: overtime_request
CREATE TABLE public.overtime_request (id integer NOT NULL DEFAULT nextval('overtime_request_id_seq'::regclass), employee_id integer NOT NULL, overtime_date date NOT NULL, start_time time without time zone NOT NULL, end_time time without time zone NOT NULL, motivation text NOT NULL, overtime_type_id integer NOT NULL, status character varying(20) NOT NULL, approved_by integer, approved_at timestamp without time zone, approval_comment text, created_at timestamp without time zone, updated_at timestamp without time zone);


-- Table: mileage_request
CREATE TABLE public.mileage_request (id integer NOT NULL DEFAULT nextval('mileage_request_id_seq'::regclass), user_id integer NOT NULL, travel_date date NOT NULL, route_addresses json NOT NULL, total_km double precision NOT NULL, calculated_km double precision, is_km_manual boolean, vehicle_id integer, vehicle_description character varying(200), cost_per_km double precision NOT NULL, total_amount double precision NOT NULL, purpose text NOT NULL, notes text, status character varying(20) NOT NULL, approved_by integer, approved_at timestamp without time zone, approval_comment text, created_at timestamp without time zone, updated_at timestamp without time zone);


-- Table: internal_message
CREATE TABLE public.internal_message (id integer NOT NULL DEFAULT nextval('internal_message_id_seq'::regclass), recipient_id integer NOT NULL, sender_id integer, title character varying(200) NOT NULL, message text NOT NULL, message_type character varying(50), is_read boolean, related_leave_request_id integer, created_at timestamp without time zone);


-- ==========================================
-- INDEXES
-- ==========================================

-- Indexes for user_role
CREATE UNIQUE INDEX user_role_name_key ON public.user_role USING btree (name);

-- Indexes for sede
CREATE UNIQUE INDEX sede_name_key ON public.sede USING btree (name);

-- Indexes for work_schedule
CREATE UNIQUE INDEX _sede_schedule_name_uc ON public.work_schedule USING btree (sede_id, name);

-- Indexes for aci_table

-- Indexes for user
CREATE UNIQUE INDEX user_username_key ON public."user" USING btree (username);
CREATE UNIQUE INDEX user_email_key ON public."user" USING btree (email);

-- Indexes for user_sede_association

-- Indexes for leave_type
CREATE UNIQUE INDEX leave_type_name_key ON public.leave_type USING btree (name);

-- Indexes for leave_request

-- Indexes for attendance_event

-- Indexes for shift_template

-- Indexes for shift

-- Indexes for presidio_coverage_template

-- Indexes for presidio_coverage

-- Indexes for reperibilita_template

-- Indexes for reperibilita_coverage

-- Indexes for reperibilita_shift

-- Indexes for intervention

-- Indexes for reperibilita_intervention

-- Indexes for holiday

-- Indexes for password_reset_token
CREATE UNIQUE INDEX password_reset_token_token_key ON public.password_reset_token USING btree (token);

-- Indexes for expense_category
CREATE UNIQUE INDEX expense_category_name_key ON public.expense_category USING btree (name);

-- Indexes for expense_report

-- Indexes for overtime_type
CREATE UNIQUE INDEX overtime_type_name_key ON public.overtime_type USING btree (name);

-- Indexes for overtime_request

-- Indexes for mileage_request

-- Indexes for internal_message


-- ==========================================
-- FOREIGN KEY CONSTRAINTS
-- ==========================================

ALTER TABLE public.work_schedule ADD CONSTRAINT work_schedule_sede_id_fkey FOREIGN KEY (sede_id) REFERENCES public.sede (id);
ALTER TABLE public."user" ADD CONSTRAINT user_sede_id_fkey FOREIGN KEY (sede_id) REFERENCES public.sede (id);
ALTER TABLE public."user" ADD CONSTRAINT user_work_schedule_id_fkey FOREIGN KEY (work_schedule_id) REFERENCES public.work_schedule (id);
ALTER TABLE public."user" ADD CONSTRAINT user_aci_vehicle_id_fkey FOREIGN KEY (aci_vehicle_id) REFERENCES public.aci_table (id);
ALTER TABLE public.user_sede_association ADD CONSTRAINT user_sede_association_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user" (id);
ALTER TABLE public.user_sede_association ADD CONSTRAINT user_sede_association_sede_id_fkey FOREIGN KEY (sede_id) REFERENCES public.sede (id);
ALTER TABLE public.leave_request ADD CONSTRAINT leave_request_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user" (id);
ALTER TABLE public.leave_request ADD CONSTRAINT leave_request_leave_type_id_fkey FOREIGN KEY (leave_type_id) REFERENCES public.leave_type (id);
ALTER TABLE public.leave_request ADD CONSTRAINT leave_request_approved_by_fkey FOREIGN KEY (approved_by) REFERENCES public."user" (id);
ALTER TABLE public.attendance_event ADD CONSTRAINT attendance_event_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user" (id);
ALTER TABLE public.attendance_event ADD CONSTRAINT attendance_event_sede_id_fkey FOREIGN KEY (sede_id) REFERENCES public.sede (id);
ALTER TABLE public.shift_template ADD CONSTRAINT shift_template_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user" (id);
ALTER TABLE public.shift ADD CONSTRAINT shift_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user" (id);
ALTER TABLE public.shift ADD CONSTRAINT shift_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user" (id);
ALTER TABLE public.presidio_coverage_template ADD CONSTRAINT presidio_coverage_template_sede_id_fkey FOREIGN KEY (sede_id) REFERENCES public.sede (id);
ALTER TABLE public.presidio_coverage_template ADD CONSTRAINT presidio_coverage_template_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user" (id);
ALTER TABLE public.presidio_coverage ADD CONSTRAINT presidio_coverage_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.presidio_coverage_template (id);
ALTER TABLE public.presidio_coverage ADD CONSTRAINT presidio_coverage_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user" (id);
ALTER TABLE public.reperibilita_template ADD CONSTRAINT reperibilita_template_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user" (id);
ALTER TABLE public.reperibilita_coverage ADD CONSTRAINT reperibilita_coverage_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user" (id);
ALTER TABLE public.reperibilita_shift ADD CONSTRAINT reperibilita_shift_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user" (id);
ALTER TABLE public.reperibilita_shift ADD CONSTRAINT reperibilita_shift_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user" (id);
ALTER TABLE public.intervention ADD CONSTRAINT intervention_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user" (id);
ALTER TABLE public.reperibilita_intervention ADD CONSTRAINT reperibilita_intervention_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user" (id);
ALTER TABLE public.reperibilita_intervention ADD CONSTRAINT reperibilita_intervention_shift_id_fkey FOREIGN KEY (shift_id) REFERENCES public.reperibilita_shift (id);
ALTER TABLE public.holiday ADD CONSTRAINT holiday_sede_id_fkey FOREIGN KEY (sede_id) REFERENCES public.sede (id);
ALTER TABLE public.holiday ADD CONSTRAINT holiday_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user" (id);
ALTER TABLE public.password_reset_token ADD CONSTRAINT password_reset_token_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user" (id);
ALTER TABLE public.expense_category ADD CONSTRAINT expense_category_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user" (id);
ALTER TABLE public.expense_report ADD CONSTRAINT expense_report_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public."user" (id);
ALTER TABLE public.expense_report ADD CONSTRAINT expense_report_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.expense_category (id);
ALTER TABLE public.expense_report ADD CONSTRAINT expense_report_approved_by_fkey FOREIGN KEY (approved_by) REFERENCES public."user" (id);
ALTER TABLE public.overtime_request ADD CONSTRAINT overtime_request_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public."user" (id);
ALTER TABLE public.overtime_request ADD CONSTRAINT overtime_request_overtime_type_id_fkey FOREIGN KEY (overtime_type_id) REFERENCES public.overtime_type (id);
ALTER TABLE public.overtime_request ADD CONSTRAINT overtime_request_approved_by_fkey FOREIGN KEY (approved_by) REFERENCES public."user" (id);
ALTER TABLE public.mileage_request ADD CONSTRAINT mileage_request_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user" (id);
ALTER TABLE public.mileage_request ADD CONSTRAINT mileage_request_vehicle_id_fkey FOREIGN KEY (vehicle_id) REFERENCES public.aci_table (id);
ALTER TABLE public.mileage_request ADD CONSTRAINT mileage_request_approved_by_fkey FOREIGN KEY (approved_by) REFERENCES public."user" (id);
ALTER TABLE public.internal_message ADD CONSTRAINT internal_message_recipient_id_fkey FOREIGN KEY (recipient_id) REFERENCES public."user" (id);
ALTER TABLE public.internal_message ADD CONSTRAINT internal_message_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public."user" (id);
ALTER TABLE public.internal_message ADD CONSTRAINT internal_message_related_leave_request_id_fkey FOREIGN KEY (related_leave_request_id) REFERENCES public.leave_request (id);


-- ==========================================
-- BASIC DATA INSERTS
-- ==========================================

-- Default user roles
INSERT INTO user_role (name, display_name, description, permissions, active, created_at) VALUES
('Admin', 'Amministratore', 'Accesso completo al sistema', '{}', true, NOW()),
('Manager', 'Manager', 'Gestione team e approvazioni', '{}', true, NOW()),
('Employee', 'Dipendente', 'Accesso base per dipendenti', '{}', true, NOW()),
('HR', 'Risorse Umane', 'Gestione personale e ferie', '{}', true, NOW());

-- Default leave type
INSERT INTO leave_type (name, description, requires_approval, max_days_per_year, active, created_at) VALUES
('Ferie', 'Ferie annuali', true, 26, true, NOW());

-- Default expense category (will need existing user)
-- INSERT INTO expense_category (name, description, active, created_by, created_at) VALUES
-- ('Trasporti', 'Spese di trasporto e trasferte', true, 1, NOW());

-- Default overtime type
INSERT INTO overtime_type (name, description, hourly_rate, active, created_at) VALUES
('Straordinario', 'Ore di straordinario standard', 15.00, true, NOW());

-- Complete database creation script generated successfully
-- Run this script in a PostgreSQL database to recreate the Workly schema

