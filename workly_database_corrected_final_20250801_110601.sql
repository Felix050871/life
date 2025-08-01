Exporting complete database structure and data...
                                        ?column?                                         
-----------------------------------------------------------------------------------------
 CREATE TABLE aci_table (                                                               +
     id INTEGER NOT NULL DEFAULT nextval('aci_table_id_seq'::regclass),                 +
     tipologia VARCHAR(100) NOT NULL,                                                   +
     marca VARCHAR(100) NOT NULL,                                                       +
     modello VARCHAR(200) NOT NULL,                                                     +
     costo_km DECIMAL NOT NULL,                                                         +
     fringe_benefit_10 DECIMAL,                                                         +
     fringe_benefit_25 DECIMAL,                                                         +
     fringe_benefit_30 DECIMAL,                                                         +
     fringe_benefit_50 DECIMAL,                                                         +
     created_at TIMESTAMP,                                                              +
     updated_at TIMESTAMP                                                               +
 );
 CREATE TABLE attendance_event (                                                        +
     id INTEGER NOT NULL DEFAULT nextval('attendance_event_id_seq'::regclass),          +
     user_id INTEGER NOT NULL,                                                          +
     date DATE NOT NULL,                                                                +
     event_type VARCHAR(20) NOT NULL,                                                   +
     timestamp TIMESTAMP NOT NULL,                                                      +
     notes TEXT,                                                                        +
     shift_status VARCHAR(20),                                                          +
     created_at TIMESTAMP,                                                              +
     sede_id INTEGER                                                                    +
 );
 CREATE TABLE expense_category (                                                        +
     id INTEGER NOT NULL DEFAULT nextval('expense_category_id_seq'::regclass),          +
     name VARCHAR(100) NOT NULL,                                                        +
     description VARCHAR(255),                                                          +
     active BOOLEAN DEFAULT true,                                                       +
     created_at TIMESTAMP,                                                              +
     created_by INTEGER NOT NULL                                                        +
 );
 CREATE TABLE expense_report (                                                          +
     id INTEGER NOT NULL DEFAULT nextval('expense_report_id_seq'::regclass),            +
     employee_id INTEGER NOT NULL,                                                      +
     expense_date DATE NOT NULL,                                                        +
     description TEXT NOT NULL,                                                         +
     amount DECIMAL NOT NULL,                                                           +
     category_id INTEGER NOT NULL,                                                      +
     receipt_filename VARCHAR(255),                                                     +
     status VARCHAR(20) NOT NULL,                                                       +
     approved_by INTEGER,                                                               +
     approved_at TIMESTAMP,                                                             +
     approval_comment TEXT,                                                             +
     created_at TIMESTAMP,                                                              +
     updated_at TIMESTAMP                                                               +
 );
 CREATE TABLE holiday (                                                                 +
     id INTEGER NOT NULL DEFAULT nextval('holiday_id_seq'::regclass),                   +
     name VARCHAR(100) NOT NULL,                                                        +
     month INTEGER NOT NULL,                                                            +
     day INTEGER NOT NULL,                                                              +
     active BOOLEAN NOT NULL DEFAULT true,                                              +
     description VARCHAR(200),                                                          +
     created_at TIMESTAMP,                                                              +
     created_by INTEGER NOT NULL,                                                       +
     sede_id INTEGER                                                                    +
 );
 CREATE TABLE internal_message (                                                        +
     id INTEGER NOT NULL DEFAULT nextval('internal_message_id_seq'::regclass),          +
     recipient_id INTEGER NOT NULL,                                                     +
     sender_id INTEGER,                                                                 +
     title VARCHAR(200) NOT NULL,                                                       +
     message TEXT NOT NULL,                                                             +
     message_type VARCHAR(50),                                                          +
     is_read BOOLEAN,                                                                   +
     related_leave_request_id INTEGER,                                                  +
     created_at TIMESTAMP                                                               +
 );
 CREATE TABLE intervention (                                                            +
     id INTEGER NOT NULL DEFAULT nextval('intervention_id_seq'::regclass),              +
     user_id INTEGER NOT NULL,                                                          +
     start_datetime TIMESTAMP NOT NULL,                                                 +
     end_datetime TIMESTAMP,                                                            +
     description TEXT,                                                                  +
     priority VARCHAR(10) NOT NULL,                                                     +
     is_remote BOOLEAN NOT NULL,                                                        +
     created_at TIMESTAMP                                                               +
 );
 CREATE TABLE leave_request (                                                           +
     id INTEGER NOT NULL DEFAULT nextval('leave_request_id_seq'::regclass),             +
     user_id INTEGER NOT NULL,                                                          +
     start_date DATE NOT NULL,                                                          +
     end_date DATE NOT NULL,                                                            +
     leave_type VARCHAR(50) NOT NULL,                                                   +
     reason TEXT,                                                                       +
     status VARCHAR(20),                                                                +
     approved_by INTEGER,                                                               +
     approved_at TIMESTAMP,                                                             +
     created_at TIMESTAMP,                                                              +
     start_time TIME,                                                                   +
     end_time TIME,                                                                     +
     leave_type_id INTEGER                                                              +
 );
 CREATE TABLE leave_type (                                                              +
     id INTEGER NOT NULL DEFAULT nextval('leave_type_id_seq'::regclass),                +
     name VARCHAR(100) NOT NULL,                                                        +
     description TEXT,                                                                  +
     requires_approval BOOLEAN,                                                         +
     active BOOLEAN DEFAULT true,                                                       +
     created_at TIMESTAMP,                                                              +
     updated_at TIMESTAMP                                                               +
 );
 CREATE TABLE mileage_request (                                                         +
     id INTEGER NOT NULL DEFAULT nextval('mileage_request_id_seq'::regclass),           +
     user_id INTEGER NOT NULL,                                                          +
     travel_date DATE NOT NULL,                                                         +
     route_addresses JSON NOT NULL,                                                     +
     total_km DOUBLE PRECISION NOT NULL,                                                +
     calculated_km DOUBLE PRECISION,                                                    +
     is_km_manual BOOLEAN,                                                              +
     vehicle_id INTEGER,                                                                +
     vehicle_description VARCHAR(200),                                                  +
     cost_per_km DOUBLE PRECISION NOT NULL,                                             +
     total_amount DOUBLE PRECISION NOT NULL,                                            +
     purpose TEXT NOT NULL,                                                             +
     notes TEXT,                                                                        +
     status VARCHAR(20) NOT NULL,                                                       +
     approved_by INTEGER,                                                               +
     approved_at TIMESTAMP,                                                             +
     approval_comment TEXT,                                                             +
     created_at TIMESTAMP,                                                              +
     updated_at TIMESTAMP                                                               +
 );
 CREATE TABLE overtime_request (                                                        +
     id INTEGER NOT NULL DEFAULT nextval('overtime_request_id_seq'::regclass),          +
     employee_id INTEGER NOT NULL,                                                      +
     overtime_date DATE NOT NULL,                                                       +
     start_time TIME NOT NULL,                                                          +
     end_time TIME NOT NULL,                                                            +
     motivation TEXT NOT NULL,                                                          +
     overtime_type_id INTEGER NOT NULL,                                                 +
     status VARCHAR(20) NOT NULL,                                                       +
     approved_by INTEGER,                                                               +
     approved_at TIMESTAMP,                                                             +
     approval_comment TEXT,                                                             +
     created_at TIMESTAMP,                                                              +
     updated_at TIMESTAMP                                                               +
 );
 CREATE TABLE overtime_type (                                                           +
     id INTEGER NOT NULL DEFAULT nextval('overtime_type_id_seq'::regclass),             +
     name VARCHAR(100) NOT NULL,                                                        +
     description TEXT,                                                                  +
     hourly_rate_multiplier DOUBLE PRECISION,                                           +
     active BOOLEAN,                                                                    +
     created_at TIMESTAMP                                                               +
 );
 CREATE TABLE password_reset_token (                                                    +
     id INTEGER NOT NULL DEFAULT nextval('password_reset_token_id_seq'::regclass),      +
     user_id INTEGER NOT NULL,                                                          +
     token VARCHAR(100) NOT NULL,                                                       +
     expires_at TIMESTAMP NOT NULL,                                                     +
     used BOOLEAN NOT NULL,                                                             +
     created_at TIMESTAMP                                                               +
 );
 CREATE TABLE presidio_coverage (                                                       +
     id INTEGER NOT NULL DEFAULT nextval('presidio_coverage_id_seq'::regclass),         +
     day_of_week INTEGER NOT NULL,                                                      +
     start_time TIME NOT NULL,                                                          +
     end_time TIME NOT NULL,                                                            +
     required_roles TEXT NOT NULL,                                                      +
     description VARCHAR(200),                                                          +
     active BOOLEAN DEFAULT true,                                                       +
     start_date DATE NOT NULL,                                                          +
     end_date DATE NOT NULL,                                                            +
     created_by INTEGER NOT NULL,                                                       +
     created_at TIMESTAMP,                                                              +
     template_id INTEGER,                                                               +
     role_count INTEGER DEFAULT 1,                                                      +
     break_start TIME,                                                                  +
     break_end TIME                                                                     +
 );
 CREATE TABLE presidio_coverage_template (                                              +
     id INTEGER NOT NULL DEFAULT nextval('presidio_coverage_template_id_seq'::regclass),+
     name VARCHAR(100) NOT NULL,                                                        +
     start_date DATE NOT NULL,                                                          +
     end_date DATE NOT NULL,                                                            +
     description VARCHAR(200),                                                          +
     active BOOLEAN DEFAULT true,                                                       +
     created_by INTEGER NOT NULL,                                                       +
     created_at TIMESTAMP,                                                              +
     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,                                    +
     sede_id INTEGER                                                                    +
 );
 CREATE TABLE reperibilita_coverage (                                                   +
     id INTEGER NOT NULL DEFAULT nextval('reperibilita_coverage_id_seq'::regclass),     +
     day_of_week INTEGER NOT NULL,                                                      +
     start_time TIME NOT NULL,                                                          +
     end_time TIME NOT NULL,                                                            +
     required_roles TEXT NOT NULL,                                                      +
     description VARCHAR(200),                                                          +
     active BOOLEAN DEFAULT true,                                                       +
     start_date DATE NOT NULL,                                                          +
     end_date DATE NOT NULL,                                                            +
     created_by INTEGER NOT NULL,                                                       +
     created_at TIMESTAMP,                                                              +
     sedi_ids TEXT                                                                      +
 );
 CREATE TABLE reperibilita_intervention (                                               +
     id INTEGER NOT NULL DEFAULT nextval('reperibilita_intervention_id_seq'::regclass), +
     user_id INTEGER NOT NULL,                                                          +
     shift_id INTEGER,                                                                  +
     start_datetime TIMESTAMP NOT NULL,                                                 +
     end_datetime TIMESTAMP,                                                            +
     description TEXT,                                                                  +
     priority VARCHAR(10) NOT NULL,                                                     +
     is_remote BOOLEAN NOT NULL,                                                        +
     created_at TIMESTAMP                                                               +
 );
 CREATE TABLE reperibilita_shift (                                                      +
     id INTEGER NOT NULL DEFAULT nextval('reperibilita_shift_id_seq'::regclass),        +
     user_id INTEGER NOT NULL,                                                          +
     date DATE NOT NULL,                                                                +
     start_time TIME NOT NULL,                                                          +
     end_time TIME NOT NULL,                                                            +
     description VARCHAR(200),                                                          +
     created_at TIMESTAMP,                                                              +
     created_by INTEGER NOT NULL                                                        +
 );
 CREATE TABLE reperibilita_template (                                                   +
     id INTEGER NOT NULL DEFAULT nextval('reperibilita_template_id_seq'::regclass),     +
     name VARCHAR(100) NOT NULL,                                                        +
     start_date DATE NOT NULL,                                                          +
     end_date DATE NOT NULL,                                                            +
     description TEXT,                                                                  +
     created_by INTEGER NOT NULL,                                                       +
     created_at TIMESTAMP                                                               +
 );
 CREATE TABLE sede (                                                                    +
     id INTEGER NOT NULL DEFAULT nextval('sede_id_seq'::regclass),                      +
     name VARCHAR(100) NOT NULL,                                                        +
     address VARCHAR(200),                                                              +
     description TEXT,                                                                  +
     active BOOLEAN NOT NULL,                                                           +
     created_at TIMESTAMP,                                                              +
     tipologia VARCHAR(20) DEFAULT 'Oraria'::character varying                          +
 );
 CREATE TABLE shift (                                                                   +
     id INTEGER NOT NULL DEFAULT nextval('shift_id_seq'::regclass),                     +
     user_id INTEGER NOT NULL,                                                          +
     date DATE NOT NULL,                                                                +
     start_time TIME NOT NULL,                                                          +
     end_time TIME NOT NULL,                                                            +
     shift_type VARCHAR(50) NOT NULL,                                                   +
     created_at TIMESTAMP,                                                              +
     created_by INTEGER NOT NULL                                                        +
 );
 CREATE TABLE shift_template (                                                          +
     id INTEGER NOT NULL DEFAULT nextval('shift_template_id_seq'::regclass),            +
     name VARCHAR(100) NOT NULL,                                                        +
     start_date DATE NOT NULL,                                                          +
     end_date DATE NOT NULL,                                                            +
     description TEXT,                                                                  +
     created_by INTEGER NOT NULL,                                                       +
     created_at TIMESTAMP                                                               +
 );
 CREATE TABLE user (                                                                    +
     id INTEGER NOT NULL DEFAULT nextval('user_id_seq'::regclass),                      +
     username VARCHAR(80) NOT NULL,                                                     +
     email VARCHAR(120) NOT NULL,                                                       +
     password_hash VARCHAR(256) NOT NULL,                                               +
     role VARCHAR(50) NOT NULL,                                                         +
     first_name VARCHAR(100) NOT NULL,                                                  +
     last_name VARCHAR(100) NOT NULL,                                                   +
     sede_id INTEGER,                                                                   +
     active BOOLEAN,                                                                    +
     part_time_percentage DOUBLE PRECISION,                                             +
     created_at TIMESTAMP,                                                              +
     all_sedi BOOLEAN DEFAULT false,                                                    +
     work_schedule_id INTEGER,                                                          +
     aci_vehicle_id INTEGER                                                             +
 );
 CREATE TABLE user_role (                                                               +
     id INTEGER NOT NULL DEFAULT nextval('user_role_id_seq'::regclass),                 +
     name VARCHAR(50) NOT NULL,                                                         +
     display_name VARCHAR(100) NOT NULL,                                                +
     description TEXT,                                                                  +
     permissions JSON,                                                                  +
     active BOOLEAN,                                                                    +
     created_at TIMESTAMP                                                               +
 );
 CREATE TABLE user_sede_association (                                                   +
     user_id INTEGER NOT NULL,                                                          +
     sede_id INTEGER NOT NULL                                                           +
 );
 CREATE TABLE work_schedule (                                                           +
     id INTEGER NOT NULL DEFAULT nextval('work_schedule_id_seq'::regclass),             +
     sede_id INTEGER NOT NULL,                                                          +
     name VARCHAR(100) NOT NULL,                                                        +
     start_time TIME,                                                                   +
     end_time TIME,                                                                     +
     description TEXT,                                                                  +
     active BOOLEAN NOT NULL,                                                           +
     created_at TIMESTAMP,                                                              +
     days_of_week JSON,                                                                 +
     start_time_min TIME,                                                               +
     start_time_max TIME,                                                               +
     end_time_min TIME,                                                                 +
     end_time_max TIME                                                                  +
 );
(26 rows)

