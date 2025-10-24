# =============================================================================
# LIFE - DATABASE MODELS
# Organized by functional areas for better maintainability
# =============================================================================
#
# MODEL ORGANIZATION:
# 1. Global Utilities & Associations
# 2. User Management Models (UserRole, User)
# 3. Attendance & Time Tracking Models (AttendanceEvent)
# 4. Leave Management Models (LeaveType, LeaveRequest)
# 5. Shift Management Models (Shift, ShiftTemplate, PresidioCoverageTemplate, PresidioCoverage)
# 6. Reperibilità Models (ReperibilitaCoverage, ReperibilitaShift, ReperibilitaIntervention, ReperibilitaTemplate)
# 7. Intervention Models (Intervention)
# 8. Administrative Models (Holiday, InternalMessage, PasswordResetToken)
# 9. Expense Management Models (ExpenseCategory, ExpenseReport)
# 10. Overtime Management Models (OvertimeType, OvertimeRequest)
# 11. Mileage Management Models (MileageRequest)
# 12. System Configuration Models (Sede, WorkSchedule, ACITable)
#
# Total Models: 25
# =============================================================================

# Core imports
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from flask_login import UserMixin
from app import db


# =============================================================================
# GLOBAL UTILITIES & ASSOCIATIONS
# =============================================================================

def italian_now():
    """Funzione helper per timestamp italiano"""
    return datetime.now(ZoneInfo('Europe/Rome'))

def convert_to_italian_time(timestamp):
    """Converte un timestamp dal database all'orario italiano"""
    if timestamp is None:
        return None
    
    # Se il timestamp non ha timezone, assumiamo che sia UTC
    if timestamp.tzinfo is None:
        utc_tz = ZoneInfo('UTC')
        timestamp = timestamp.replace(tzinfo=utc_tz)
    
    # Converti all'orario italiano
    return timestamp.astimezone(ZoneInfo('Europe/Rome'))

# Tabella di associazione many-to-many tra User e Sede
user_sede_association = db.Table('user_sede_association',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('sede_id', db.Integer, db.ForeignKey('sede.id'), primary_key=True)
)

# =============================================================================
# USER MANAGEMENT MODELS
# =============================================================================

class UserRole(db.Model):
    """Modello per la gestione dinamica dei ruoli utente"""
    __table_args__ = (
        db.UniqueConstraint('name', 'company_id', name='_name_company_uc'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # Rimosso unique=True, ora in UniqueConstraint
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    permissions = db.Column(db.JSON, default=dict)  # Permessi in formato JSON
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=italian_now)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)  # Multi-tenant
    
    company = db.relationship('Company', backref='user_roles')
    
    def __repr__(self):
        return f'<UserRole {self.display_name}>'
    
    def has_permission(self, permission):
        """Verifica se il ruolo ha un determinato permesso"""
        return self.permissions.get(permission, False)
    
    @classmethod
    def get_available_permissions(cls):
        """Restituisce la lista completa dei permessi disponibili con traduzioni"""
        return {
            # Dashboard e sistema base
            'can_access_dashboard': 'Dashboard',
            
            # Gestione ruoli
            'can_manage_roles': 'Gestire Ruoli',
            'can_view_roles': 'Visualizzare Ruoli',
            
            # Gestione utenti
            'can_manage_users': 'Gestire Utenti',
            'can_view_users': 'Visualizzare Utenti',
            
            # Gestione sedi
            'can_manage_sedi': 'Gestire Sedi',
            'can_view_sedi': 'Visualizzare Sedi',
            
            # Gestione orari/scheduli
            'can_manage_schedules': 'Gestire Orari',
            'can_view_schedules': 'Visualizzare Orari',
            
            # Gestione turni
            'can_manage_shifts': 'Gestione Coperture',
            'can_view_shifts': 'Visualizza Coperture',
            
            # Reperibilità
            'can_manage_reperibilita': 'Gestire Reperibilità',
            'can_view_reperibilita': 'Visualizzare Tutte le Reperibilità',
            'can_view_my_reperibilita': 'Visualizzare Le Mie Reperibilità',
            'can_manage_coverage': 'Gestire Coperture Reperibilità',
            'can_view_coverage': 'Visualizzare Coperture Reperibilità',
            
            # Gestione presenze
            'can_manage_attendance': 'Gestire Presenze',
            'can_view_attendance': 'Visualizzare Tutte le Presenze',
            'can_view_my_attendance': 'Visualizzare Le Mie Presenze',
            'can_access_attendance': 'Accedere alle Presenze',
            'can_view_sede_attendance': 'Visualizzare Presenze Sede',
            
            # Gestione ferie/permessi
            'can_manage_leave': 'Gestisci Tipologie Ferie/Permessi',
            'can_manage_leave_types': 'Gestire Tipologie Permessi',
            'can_approve_leave': 'Approvare Ferie/Permessi',
            'can_request_leave': 'Richiedere Ferie/Permessi',
            'can_view_leave': 'Visualizzare Tutte le Ferie/Permessi',
            'can_view_my_leave': 'Visualizzare Le Mie Ferie/Permessi',
            
            # Gestione interventi
            'can_manage_interventions': 'Gestire Interventi',
            'can_view_interventions': 'Visualizzare Tutti gli Interventi',
            'can_view_my_interventions': 'Visualizzare I Miei Interventi',
            
            # Gestione festività
            'can_manage_holidays': 'Gestire Festività',
            'can_view_holidays': 'Visualizzare Festività',
            
            # Gestione QR
            'can_manage_qr': 'Gestire QR',
            'can_view_qr': 'Visualizzare QR',
            
            # Report e statistiche
            'can_view_reports': 'Visualizzare Report',
            'can_manage_reports': 'Gestire Report',
            'can_view_statistics': 'Visualizzare Statistiche',
            
            # Messaggi
            'can_send_messages': 'Inviare Messaggi',
            'can_view_messages': 'Visualizzare Messaggi',
            
            # Note spese
            'can_manage_expense_reports': 'Gestire Note Spese',
            'can_view_expense_reports': 'Visualizzare Tutte le Note Spese',
            'can_view_my_expense_reports': 'Visualizzare Le Mie Note Spese',
            'can_approve_expense_reports': 'Approvare Note Spese',
            'can_create_expense_reports': 'Creare Note Spese',
            
            # Straordinari
            'can_create_overtime_requests': 'Creare Richieste Straordinario',
            'can_view_overtime_requests': 'Visualizzare Tutte le Richieste Straordinario',
            'can_view_my_overtime_requests': 'Visualizzare Le Mie Richieste Straordinario',
            'can_manage_overtime_requests': 'Gestire Richieste Straordinario',
            'can_approve_overtime_requests': 'Approvare Richieste Straordinario',
            'can_create_overtime_types': 'Creare Tipologie Straordinario',
            'can_view_overtime_types': 'Visualizzare Tipologie Straordinario',
            'can_manage_overtime_types': 'Gestisci Tipologie Straordinari',
            
            # Dashboard Widget Permissions
            'can_view_team_stats_widget': 'Widget Statistiche Team',
            'can_view_my_attendance_widget': 'Widget Le Mie Presenze',
            'can_view_team_management_widget': 'Widget Gestione Team',
            'can_view_my_leave_requests_widget': 'Widget Le Mie Richieste',
            'can_view_my_shifts_widget': 'Widget I Miei Turni', 
            'can_view_my_reperibilita_widget': 'Widget Le Mie Reperibilità',
            'can_view_expense_reports_widget': 'Widget Note Spese',
            'can_view_leave_requests_widget': 'Widget Ferie/Permessi',
            'can_view_daily_attendance_widget': 'Widget Presenze per Sede',
            'can_view_shifts_coverage_widget': 'Widget Coperture Turni',
            'can_view_reperibilita_widget': 'Widget Reperibilità',
            'can_view_my_overtime_requests_widget': 'Widget Le Mie Richieste Straordinario',
            'can_view_overtime_management_widget': 'Widget Gestione Straordinari',
            'can_view_overtime_widget': 'Widget Straordinari',
            'can_view_my_overtime_widget': 'Widget I Miei Straordinari',
            
            # Rimborsi chilometrici
            'can_create_mileage_requests': 'Creare Richieste Rimborso Km',
            'can_view_mileage_requests': 'Visualizzare Tutte le Richieste Rimborso Km',
            'can_view_my_mileage_requests': 'Visualizzare Le Mie Richieste Rimborso Km',
            'can_approve_mileage_requests': 'Approvare Richieste Rimborso Km',
            'can_manage_mileage_requests': 'Gestire Richieste Rimborso Km',
            'can_view_mileage_widget': 'Widget Rimborsi Chilometrici',
            'can_view_my_mileage_widget': 'Widget I Miei Rimborsi',
            
            # Banca ore
            'can_view_banca_ore_widget': 'Widget Banca Ore',
            'can_view_my_banca_ore_widget': 'Widget La Mia Banca Ore',
            
            # Tabelle ACI
            'can_manage_aci_tables': 'Gestire Tabelle ACI',
            'can_view_aci_tables': 'Visualizzare Tabelle ACI',
            
            # CIRCLE - Social Intranet
            'can_access_hubly': 'Accedere a CIRCLE',
            'can_create_posts': 'Creare Post/News',
            'can_edit_posts': 'Modificare Post/News',
            'can_delete_posts': 'Eliminare Post/News',
            'can_manage_groups': 'Gestire Gruppi',
            'can_create_groups': 'Creare Gruppi',
            'can_join_groups': 'Unirsi ai Gruppi',
            'can_create_polls': 'Creare Sondaggi',
            'can_vote_polls': 'Votare Sondaggi',
            'can_manage_polls': 'Gestire Sondaggi',
            'can_manage_documents': 'Gestire Documenti',
            'can_view_documents': 'Visualizzare Documenti',
            'can_upload_documents': 'Caricare Documenti',
            'can_manage_calendar': 'Gestire Calendario',
            'can_view_calendar': 'Visualizzare Calendario',
            'can_create_events': 'Creare Eventi',
            'can_manage_tools': 'Gestire Strumenti Esterni',
            'can_view_tools': 'Visualizzare Strumenti',
            'can_comment_posts': 'Commentare Post',
            'can_like_posts': 'Mettere Like ai Post',
            
            # HR - Human Resources
            'can_manage_hr_data': 'Gestire Dati HR',
            'can_view_hr_data': 'Visualizzare Tutti i Dati HR',
            'can_view_my_hr_data': 'Visualizzare I Miei Dati HR',
            
            # Commesse - Project Management
            'can_manage_commesse': 'Gestire Commesse',
            'can_view_commesse': 'Visualizzare Commesse'
        }

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)  # Unique constraint removed, now scoped by company
    email = db.Column(db.String(120), nullable=False)  # Unique constraint removed, now scoped by company
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # Ora referenzia UserRole.name
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=True)  # Sede principale (legacy)
    all_sedi = db.Column(db.Boolean, default=False)  # True se l'utente può accedere a tutte le sedi
    work_schedule_id = db.Column(db.Integer, db.ForeignKey('work_schedule.id'), nullable=True)  # Orario di lavoro specifico
    aci_vehicle_id = db.Column(db.Integer, db.ForeignKey('aci_table.id'), nullable=True)  # Veicolo ACI per rimborsi km
    active = db.Column(db.Boolean, default=True)  # Renamed to avoid UserMixin conflict
    part_time_percentage = db.Column(db.Float, default=100.0)  # Percentuale di lavoro: 100% = tempo pieno, 50% = metà tempo, ecc.
    overtime_enabled = db.Column(db.Boolean, default=False)  # True se l'utente è abilitato a fare straordinari
    overtime_type = db.Column(db.String(50), nullable=True)  # "Straordinario Pagato" o "Banca Ore"
    banca_ore_limite_max = db.Column(db.Float, default=40.0)  # Limite massimo di ore accumulabili (solo per Banca Ore)
    banca_ore_periodo_mesi = db.Column(db.Integer, default=12)  # Periodo in mesi per usufruire ore (solo per Banca Ore)
    profile_image = db.Column(db.String(255), nullable=True)  # Path dell'immagine del profilo
    created_at = db.Column(db.DateTime, default=italian_now)
    
    # CIRCLE Social fields
    bio = db.Column(db.Text, nullable=True)  # Biografia breve per profilo social
    linkedin_url = db.Column(db.String(255), nullable=True)  # URL profilo LinkedIn
    twitter_url = db.Column(db.String(255), nullable=True)  # URL profilo Twitter/X
    instagram_url = db.Column(db.String(255), nullable=True)  # URL profilo Instagram
    facebook_url = db.Column(db.String(255), nullable=True)  # URL profilo Facebook
    github_url = db.Column(db.String(255), nullable=True)  # URL profilo GitHub
    phone_number = db.Column(db.String(20), nullable=True)  # Numero di telefono aziendale
    department = db.Column(db.String(100), nullable=True)  # Dipartimento/Reparto
    job_title = db.Column(db.String(100), nullable=True)  # Titolo professionale
    
    # CV/Resume fields (stored as JSON for flexibility)
    education = db.Column(db.JSON, nullable=True)  # Formazione/Istruzione
    experience = db.Column(db.JSON, nullable=True)  # Esperienza lavorativa
    skills = db.Column(db.JSON, nullable=True)  # Competenze/Abilità
    languages = db.Column(db.JSON, nullable=True)  # Lingue conosciute con livelli
    certifications = db.Column(db.JSON, nullable=True)  # Certificazioni
    references = db.Column(db.Text, nullable=True)  # Referenze professionali
    
    # Multi-tenant fields
    is_system_admin = db.Column(db.Boolean, default=False)  # Admin di sistema (non legato a nessuna azienda)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)  # Azienda di appartenenza
    
    # Composite unique constraints: username/email unique within company
    __table_args__ = (
        db.UniqueConstraint('company_id', 'username', name='uq_company_username'),
        db.UniqueConstraint('company_id', 'email', name='uq_company_email'),
    )
    
    # Relationship con Sede, WorkSchedule, ACITable e Company
    sede_obj = db.relationship('Sede', backref='users')
    work_schedule = db.relationship('WorkSchedule', backref='assigned_users')
    aci_vehicle = db.relationship('ACITable', backref='assigned_users')
    company = db.relationship('Company', back_populates='users')
    
    # La relazione con AttendanceEvent è già definita tramite backref in AttendanceEvent.user
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_profile_image_url(self):
        """Restituisce l'URL dell'immagine del profilo o quella di default"""
        if self.profile_image:
            return f"/static/uploads/profiles/{self.profile_image}"
        return "/static/images/defaults/default_profile.png"
    
    def get_accessible_sedi(self):
        """Restituisce tutte le sedi accessibili dall'utente (filtrate per azienda)"""
        # System admin vedono tutte le sedi
        if self.is_system_admin:
            return Sede.query.filter_by(active=True).all()
        
        # Filtra per company_id
        base_query = Sede.query.filter_by(active=True, company_id=self.company_id)
        
        if self.all_sedi:
            return base_query.all()
        elif self.sede_id:
            return [self.sede_obj] if self.sede_obj and self.sede_obj.active and self.sede_obj.company_id == self.company_id else []
        return []
    
    def can_access_sede(self, sede_id):
        """Verifica se l'utente può accedere a una specifica sede"""
        if self.all_sedi:
            return True
        return self.sede_id == sede_id
    
    def get_sede_display(self):
        """Restituisce la descrizione delle sedi assegnate per visualizzazione"""
        if self.all_sedi:
            return "Tutte le sedi"
        elif self.sede_obj:
            return self.sede_obj.name
        return "Nessuna sede"
    
    @classmethod
    def get_visible_users_query(cls, current_user):
        """Restituisce una query degli utenti visibili per l'utente corrente.
        Applica automaticamente il filtro per sede se l'utente non è multi-sede."""
        query = cls.query
        
        if not current_user.all_sedi and current_user.sede_id:
            # Utenti sede-specifici vedono solo utenti della loro sede
            query = query.filter_by(sede_id=current_user.sede_id)
        
        return query
    
    def get_role_obj(self):
        """Ottieni l'oggetto UserRole associato"""
        return UserRole.query.filter_by(name=self.role, company_id=self.company_id).first()
    
    def has_permission(self, permission):
        """Verifica se l'utente ha un determinato permesso tramite il suo ruolo
        Controllo diretto 1:1 - ogni permesso corrisponde esattamente a una voce di menu"""
        role_obj = self.get_role_obj()
        if role_obj:
            # Controllo diretto del permesso - corrispondenza 1:1
            return role_obj.has_permission(permission)
        # Fallback per compatibilità con ruoli legacy
        return self._legacy_permissions(permission)
    
    def _legacy_permissions(self, permission):
        """Permessi legacy per retrocompatibilità - saranno rimossi quando tutti i ruoli avranno permessi"""
        # Admin ha tutti i permessi per default
        if self.role == 'Admin':
            return True
        return False
    
    def has_role(self, role_name):
        """Verifica se l'utente ha un determinato ruolo"""
        return self.role == role_name
    
    # Metodi di autorizzazione granulari per ogni funzionalità del menu
    
    # === HOME ===
    def can_access_dashboard(self):
        return self.has_permission('can_access_dashboard')
    
    # === RUOLI ===
    def can_manage_roles(self):
        return self.has_permission('can_manage_roles')
    
    def can_view_roles(self):
        return self.has_permission('can_view_roles')
    
    # === UTENTI ===
    def can_manage_users(self):
        return self.has_permission('can_manage_users')
    
    def can_view_users(self):
        return self.has_permission('can_view_users')
    
    # === SEDI ===
    def can_manage_sedi(self):
        return self.has_permission('can_manage_sedi')
    
    def can_view_sedi(self):
        return self.has_permission('can_view_sedi')
    
    # === ORARI ===
    def can_manage_schedules(self):
        return self.has_permission('can_manage_schedules')
    
    def can_view_schedules(self):
        return self.has_permission('can_view_schedules')
    
    # === TURNI ===
    def can_manage_shifts(self):
        return self.has_permission('can_manage_shifts')
    
    def can_manage_system(self):
        return self.has_permission('can_manage_system')
    
    def can_view_shifts(self):
        return self.has_permission('can_view_shifts')
    
    # === REPERIBILITÀ ===
    def can_manage_reperibilita(self):
        return self.has_permission('can_manage_reperibilita')
    
    def can_view_reperibilita(self):
        return self.has_permission('can_view_reperibilita')
    
    def can_view_my_reperibilita(self):
        """Può visualizzare le proprie reperibilità"""
        return self.has_permission('can_view_my_reperibilita')
    
    def can_manage_coverage(self):
        """Permesso per gestire coperture reperibilità"""
        return self.has_permission('can_manage_coverage')
    
    def can_view_coverage(self):
        """Permesso per visualizzare coperture reperibilità"""
        return self.has_permission('can_view_coverage')
    
    def can_access_reperibilita_menu(self):
        """Permesso per accedere al menu reperibilità"""
        return (self.can_manage_reperibilita() or self.can_view_reperibilita() or 
                self.can_view_my_reperibilita() or self.can_manage_coverage() or 
                self.can_view_coverage() or self.can_view_interventions() or 
                self.can_view_my_interventions())
    
    # === PRESENZE ===
    def can_manage_attendance(self):
        return self.has_permission('can_manage_attendance')
    
    def can_view_attendance(self):
        return self.has_permission('can_view_attendance')
    
    def can_view_my_attendance(self):
        """Può visualizzare le proprie presenze"""
        return self.has_permission('can_view_my_attendance')
    
    def can_access_attendance(self):
        return self.has_permission('can_access_attendance')
    
    def can_view_sede_attendance(self):
        """Visualizzare presenze della sede - permesso specifico"""
        return self.has_permission('can_view_sede_attendance')
    
    # === FERIE/PERMESSI ===
    def can_manage_leave(self):
        return self.has_permission('can_manage_leave')
    
    def can_approve_leave(self):
        return self.has_permission('can_approve_leave')
    
    def can_manage_leave_types(self):
        """Può gestire le tipologie di permesso"""
        return self.has_permission('can_manage_leave_types')
    
    def can_request_leave(self):
        return self.has_permission('can_request_leave')
    
    def can_view_leave(self):
        return self.has_permission('can_view_leave')
    
    def can_view_my_leave(self):
        """Può visualizzare le proprie ferie/permessi"""
        return self.has_permission('can_view_my_leave')
    
    # === INTERVENTI ===
    def can_manage_interventions(self):
        return self.has_permission('can_manage_interventions')
    
    def can_view_interventions(self):
        return self.has_permission('can_view_interventions')
    
    def can_view_my_interventions(self):
        """Può visualizzare i propri interventi"""
        return self.has_permission('can_view_my_interventions')
    
    # === FESTIVITÀ ===
    def can_manage_holidays(self):
        return self.has_permission('can_manage_holidays')
    
    def can_view_holidays(self):
        return self.has_permission('can_view_holidays')
    
    def can_access_holidays(self):
        return self.can_manage_holidays() or self.can_view_holidays()
    
    # === GESTIONE QR ===
    def can_manage_qr(self):
        return self.has_permission('can_manage_qr')
    
    def can_view_qr(self):
        return self.has_permission('can_view_qr')
    
    # === STATISTICHE ===
    def can_view_reports(self):
        return self.has_permission('can_view_reports')
    
    def can_manage_reports(self):
        return self.has_permission('can_manage_reports')
    
    def can_view_statistics(self):
        return self.has_permission('can_view_reports')
    
    # === MESSAGGI ===
    def can_send_messages(self):
        return self.has_permission('can_send_messages')
    
    def can_view_messages(self):
        return self.has_permission('can_view_messages')
    
    # === NOTE SPESE ===
    def can_manage_expense_reports(self):
        return self.has_permission('can_manage_expense_reports')
    
    def can_view_expense_reports(self):
        return self.has_permission('can_view_expense_reports')
    
    def can_approve_expense_reports(self):
        return self.has_permission('can_approve_expense_reports')
    
    def can_create_expense_reports(self):
        return self.has_permission('can_create_expense_reports')
    
    def can_view_my_expense_reports(self):
        return self.has_permission('can_view_my_expense_reports')
    
    # Metodi permessi straordinari
    def can_create_overtime_requests(self):
        return self.has_permission('can_create_overtime_requests')
    
    def can_view_overtime_requests(self):
        return self.has_permission('can_view_overtime_requests')
    
    def can_manage_overtime_requests(self):
        return self.has_permission('can_manage_overtime_requests')
    
    def can_approve_overtime_requests(self):
        return self.has_permission('can_approve_overtime_requests')
    
    def can_create_overtime_types(self):
        return self.has_permission('can_create_overtime_types')
    
    def can_view_overtime_types(self):
        return self.has_permission('can_view_overtime_types')
    
    def can_manage_overtime_types(self):
        return self.has_permission('can_manage_overtime_types')
    
    def can_view_my_overtime_requests(self):
        return self.has_permission('can_view_my_overtime_requests')
    
    # Metodi permessi rimborsi chilometrici
    def can_create_mileage_requests(self):
        return self.has_permission('can_create_mileage_requests')
    
    def can_view_mileage_requests(self):
        return self.has_permission('can_view_mileage_requests')
    
    def can_approve_mileage_requests(self):
        return self.has_permission('can_approve_mileage_requests')
    
    def can_manage_mileage_requests(self):
        return self.has_permission('can_manage_mileage_requests')
    
    def can_view_my_mileage_requests(self):
        return self.has_permission('can_view_my_mileage_requests')
    
    def can_access_turni(self):
        """Verifica se l'utente può accedere alla gestione turni"""
        return self.has_permission('can_manage_shifts') or self.has_permission('can_view_shifts')
    
    def can_access_reperibilita(self):
        """Verifica se l'utente può accedere alla gestione reperibilità"""
        return self.has_permission('can_manage_reperibilita') or self.has_permission('can_view_reperibilita')
    
    # === METODI DI ACCESSO AI MENU ===
    def can_access_roles_menu(self):
        """Accesso al menu Ruoli"""
        return self.can_manage_roles() or self.can_view_roles()
    
    def can_access_users_menu(self):
        """Accesso al menu Utenti"""
        return self.can_manage_users() or self.can_view_users()
    
    def can_access_sedi_menu(self):
        """Accesso al menu Sedi"""
        return self.can_manage_sedi() or self.can_view_sedi()
    
    def can_access_schedules_menu(self):
        """Accesso al menu Orari"""
        return self.can_manage_schedules() or self.can_view_schedules()
    
    def can_access_shifts_menu(self):
        """Accesso al menu Turni - considera anche utenti multi-sede"""
        if not self.can_access_turni():
            return False
        
        # Se l'utente ha una sede specifica, verifica se supporta i turni
        if self.sede_obj:
            return self.sede_obj.is_turni_mode()
        
        # Se l'utente ha accesso a tutte le sedi, verifica se almeno una supporta i turni
        if self.all_sedi:
            accessible_sedi = self.get_accessible_sedi()
            return any(sede.is_turni_mode() for sede in accessible_sedi)
        
        return False
    
    def get_turni_sedi(self):
        """Restituisce le sedi turni accessibili dall'utente"""
        from models import Sede
        
        if self.can_manage_shifts():
            # Utenti con permesso di gestione vedono tutte le sedi di tipo "Turni" 
            return Sede.query.filter_by(tipologia='Turni', active=True).all()
        elif self.can_view_shifts():
            # Utenti con solo permesso di visualizzazione
            if self.all_sedi:
                # Utenti multi-sede vedono tutte le sedi turni
                return Sede.query.filter_by(tipologia='Turni', active=True).all()
            elif self.sede_obj and self.sede_obj.is_turni_mode():
                # Utenti con sede specifica vedono solo la propria se supporta turni
                return [self.sede_obj]
        
        return []
    

    
    def can_access_coverage_menu(self):
        """Accesso al menu Gestione Coperture"""
        return self.can_manage_coverage() or self.can_view_coverage()
    
    def can_access_attendance_menu(self):
        """Accesso al menu Presenze"""
        return self.can_manage_attendance() or self.can_view_attendance() or self.can_access_attendance() or self.can_view_sede_attendance()
    
    def can_access_leave_menu(self):
        """Accesso al menu Ferie/Permessi"""
        return self.can_manage_leave() or self.can_approve_leave() or self.can_request_leave() or self.can_view_leave()
    
    def can_access_interventions_menu(self):
        """Accesso al menu Interventi"""
        return self.can_manage_interventions() or self.can_view_interventions() or self.can_view_my_interventions()
    
    def can_access_holidays_menu(self):
        """Accesso al menu Festività"""
        return self.can_manage_holidays() or self.can_view_holidays()
    
    def can_access_qr_menu(self):
        """Accesso al menu Gestione QR"""
        return self.can_manage_qr() or self.can_view_qr()
    
    def can_access_reports_menu(self):
        """Accesso al menu Statistiche"""
        return self.can_view_reports() or self.can_manage_reports()
    
    def can_access_messages_menu(self):
        """Accesso al menu Messaggi"""
        return self.can_send_messages() or self.can_view_messages()
    
    def can_access_expense_reports_menu(self):
        """Accesso al menu Note Spese"""
        return (self.can_manage_expense_reports() or self.can_view_expense_reports() or 
                self.can_approve_expense_reports() or self.can_create_expense_reports() or
                self.can_view_my_expense_reports())
    
    def can_access_overtime_menu(self):
        """Accesso al menu Straordinari"""
        return (self.can_create_overtime_requests() or self.can_view_overtime_requests() or 
                self.can_manage_overtime_requests() or self.can_approve_overtime_requests() or
                self.can_view_my_overtime_requests())
    
    def can_access_mileage_menu(self):
        """Accesso al menu Rimborsi Chilometrici"""
        return (self.can_create_mileage_requests() or self.can_view_mileage_requests() or 
                self.can_manage_mileage_requests() or self.can_approve_mileage_requests() or
                self.can_view_my_mileage_requests())
    
    # === HR - HUMAN RESOURCES ===
    def can_manage_hr_data(self):
        """Gestire dati HR (creare, modificare, eliminare)"""
        return self.has_permission('can_manage_hr_data')
    
    def can_view_hr_data(self):
        """Visualizzare tutti i dati HR dell'azienda"""
        return self.has_permission('can_view_hr_data')
    
    def can_view_my_hr_data(self):
        """Visualizzare i propri dati HR"""
        return self.has_permission('can_view_my_hr_data')
    
    def can_access_hr_menu(self):
        """Accesso al menu HR"""
        return self.can_manage_hr_data() or self.can_view_hr_data() or self.can_view_my_hr_data()
    
    # === COMMESSE - PROJECT MANAGEMENT ===
    def can_manage_commesse(self):
        """Gestire commesse (creare, modificare, eliminare)"""
        return self.has_permission('can_manage_commesse')
    
    def can_view_commesse(self):
        """Visualizzare commesse"""
        return self.has_permission('can_view_commesse')
    
    def can_access_commesse_menu(self):
        """Accesso al menu Commesse"""
        return self.can_manage_commesse() or self.can_view_commesse()
    
    # Dashboard widget permissions - Completamente configurabili dall'admin
    def can_view_team_stats_widget(self):
        """Widget statistiche team nella dashboard"""
        return self.has_permission('can_view_team_stats_widget')
    
    def can_view_my_attendance_widget(self):
        """Widget gestione presenze personali (entrata/uscita/pausa)"""
        return self.has_permission('can_view_my_attendance_widget')
    
    def can_view_team_management_widget(self):
        """Widget gestione team"""
        return self.has_permission('can_view_team_management_widget')
    
    def can_view_leave_requests_widget(self):
        """Widget richieste ferie/permessi"""
        return self.has_permission('can_view_leave_requests_widget')
    
    def can_view_daily_attendance_widget(self):
        """Widget presenze giornaliere per sede"""
        return self.has_permission('can_view_daily_attendance_widget')
    
    def can_view_shifts_coverage_widget(self):
        """Widget coperture turni con segnalazioni"""
        return self.has_permission('can_view_shifts_coverage_widget')
    
    def can_view_reperibilita_widget(self):
        """Widget reperibilità (personali e/o team)"""
        return self.has_permission('can_view_reperibilita_widget')
    
    def can_view_my_leave_requests_widget(self):
        """Widget richieste ferie/permessi/malattie personali"""
        return self.has_permission('can_view_my_leave_requests_widget')
    
    def can_view_my_shifts_widget(self):
        """Widget turni personali"""
        return self.has_permission('can_view_my_shifts_widget')
    
    def can_view_my_reperibilita_widget(self):
        """Widget reperibilità personali"""
        return self.has_permission('can_view_my_reperibilita_widget')
    
    def can_view_expense_reports_widget(self):
        """Widget note spese (personali e/o team)"""
        return self.has_permission('can_view_expense_reports_widget')
    
    def can_view_my_expense_reports_widget(self):
        """Widget le mie note spese personali"""
        return self.has_permission('can_view_my_expense_reports')
    
    def can_view_overtime_widget(self):
        """Può visualizzare widget straordinari"""
        return self.has_permission('can_view_overtime_widget')
        
    def can_view_my_overtime_widget(self):
        """Può visualizzare widget dei propri straordinari"""
        return self.has_permission('can_view_my_overtime_widget')
    
    def can_view_mileage_widget(self):
        """Può visualizzare widget rimborsi chilometrici"""
        return self.has_permission('can_view_mileage_widget')
        
    def can_view_my_mileage_widget(self):
        """Può visualizzare widget dei propri rimborsi chilometrici"""
        return self.has_permission('can_view_my_mileage_widget')
    
    def can_view_banca_ore_widget(self):
        """Può visualizzare widget banca ore"""
        return self.has_permission('can_view_banca_ore_widget')
    
    def can_view_my_banca_ore_widget(self):
        """Può visualizzare widget della propria banca ore"""
        return (self.has_permission('can_view_my_banca_ore_widget') and 
                self.overtime_enabled and self.overtime_type == 'Banca Ore')
    
    # === TABELLE ACI ===
    def can_manage_aci_tables(self):
        """Può gestire le tabelle ACI"""
        return self.has_permission('can_manage_aci_tables')
    
    def can_view_aci_tables(self):
        """Può visualizzare le tabelle ACI"""
        return self.has_permission('can_view_aci_tables')
    
    def can_access_aci_tables_menu(self):
        """Accesso al menu Tabelle ACI"""
        return self.can_manage_aci_tables() or self.can_view_aci_tables()
    
    def get_sede_name(self):
        """Ottieni il nome della sede associata all'utente"""
        return self.sede_obj.name if self.sede_obj else "Nessuna sede"
    
    def should_check_attendance_timing(self):
        """Determina se il sistema deve controllare ritardi/anticipi per questo utente"""
        # Gli utenti senza orario assegnato (work_schedule_id è None) o con orario 'Turni'
        # possono registrare presenze ma non verranno controllati per ritardi/anticipi
        if self.work_schedule_id is None:
            return False
        
        if self.work_schedule and self.work_schedule.is_turni_schedule():
            return False
            
        return True
    
    def can_view_all_attendance(self):
        """Verifica se l'utente può visualizzare le presenze di tutti gli utenti"""
        return self.can_manage_attendance()
    

    
    def can_view_all_reperibilita(self):
        """Verifica se l'utente può visualizzare tutte le reperibilità"""
        return self.can_manage_reperibilita()
    
    def get_sedi_list(self):
        """Restituisce la lista delle sedi associate all'utente (per compatibilità template)"""
        if self.sede_obj:
            return [self.sede_obj.name]
        return []
    
    def get_last_attendance_date(self):
        """Restituisce la data dell'ultima presenza dell'utente"""
        last_attendance = AttendanceEvent.query.filter_by(user_id=self.id).order_by(AttendanceEvent.date.desc()).first()
        if last_attendance:
            return last_attendance.date
        return None
    
    # === CONNECTION MANAGEMENT (CIRCLE) ===
    def is_connected_with(self, other_user):
        """Verifica se due utenti sono connessi (richiesta accettata)"""
        connection = ConnectionRequest.query.filter(
            db.or_(
                db.and_(
                    ConnectionRequest.sender_id == self.id,
                    ConnectionRequest.recipient_id == other_user.id
                ),
                db.and_(
                    ConnectionRequest.sender_id == other_user.id,
                    ConnectionRequest.recipient_id == self.id
                )
            ),
            ConnectionRequest.status == 'accepted'
        ).first()
        return connection is not None
    
    def has_pending_request_with(self, other_user):
        """Verifica se esiste una richiesta pendente con un altro utente"""
        pending = ConnectionRequest.query.filter(
            db.or_(
                db.and_(
                    ConnectionRequest.sender_id == self.id,
                    ConnectionRequest.recipient_id == other_user.id
                ),
                db.and_(
                    ConnectionRequest.sender_id == other_user.id,
                    ConnectionRequest.recipient_id == self.id
                )
            ),
            ConnectionRequest.status == 'pending'
        ).first()
        return pending
    
    def get_connection_status(self, other_user):
        """Restituisce lo stato della connessione con un altro utente
        Returns: 'connected', 'pending_sent', 'pending_received', 'none'
        """
        if self.id == other_user.id:
            return 'self'
        
        # Check if connected
        if self.is_connected_with(other_user):
            return 'connected'
        
        # Check pending request
        pending = self.has_pending_request_with(other_user)
        if pending:
            if pending.sender_id == self.id:
                return 'pending_sent'
            else:
                return 'pending_received'
        
        return 'none'
    
    def get_connections(self):
        """Restituisce tutti gli utenti connessi"""
        # Richieste inviate e accettate
        sent_accepted = db.session.query(User).join(
            ConnectionRequest, 
            ConnectionRequest.recipient_id == User.id
        ).filter(
            ConnectionRequest.sender_id == self.id,
            ConnectionRequest.status == 'accepted'
        ).all()
        
        # Richieste ricevute e accettate
        received_accepted = db.session.query(User).join(
            ConnectionRequest,
            ConnectionRequest.sender_id == User.id
        ).filter(
            ConnectionRequest.recipient_id == self.id,
            ConnectionRequest.status == 'accepted'
        ).all()
        
        # Unisci e rimuovi duplicati
        connections = list(set(sent_accepted + received_accepted))
        return connections
    
    def get_pending_connection_requests(self):
        """Restituisce tutte le richieste di connessione pendenti ricevute"""
        return ConnectionRequest.query.filter_by(
            recipient_id=self.id,
            status='pending'
        ).all()


class UserHRData(db.Model):
    """Modello per gestire dati HR (Human Resources) degli utenti
    Separato dal modello User per privacy, sicurezza e performance.
    Relazione 1-to-1 con User."""
    
    __tablename__ = 'user_hr_data'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    
    # Dati anagrafici
    matricola = db.Column(db.String(50), nullable=True)  # Employee number
    codice_fiscale = db.Column(db.String(16), nullable=True)  # Tax code
    birth_date = db.Column(db.Date, nullable=True)  # Data di nascita
    birth_city = db.Column(db.String(100), nullable=True)  # Città di nascita
    birth_province = db.Column(db.String(2), nullable=True)  # Provincia di nascita (sigla)
    birth_country = db.Column(db.String(100), nullable=True, default='Italia')  # Paese di nascita
    gender = db.Column(db.String(1), nullable=True)  # M/F/A (altro)
    
    # Residenza e domicilio
    address = db.Column(db.String(255), nullable=True)  # Indirizzo residenza
    city = db.Column(db.String(100), nullable=True)  # Città residenza
    province = db.Column(db.String(2), nullable=True)  # Provincia (sigla)
    postal_code = db.Column(db.String(10), nullable=True)  # CAP
    country = db.Column(db.String(100), nullable=True, default='Italia')  # Paese
    alternative_domicile = db.Column(db.String(255), nullable=True)  # Domicilio se diverso dalla residenza
    phone = db.Column(db.String(20), nullable=True)  # Recapito telefonico personale
    law_104_benefits = db.Column(db.Boolean, default=False)  # Fruizione permessi L. 104/92
    personal_email = db.Column(db.String(120), nullable=True)  # Email personale
    
    # Dati contrattuali
    contract_type = db.Column(db.String(100), nullable=True)  # Tipo contratto (TD, TI, Stage, ecc.)
    distacco_supplier = db.Column(db.String(200), nullable=True)  # Azienda distaccante (solo per "In Distacco")
    consulente_vat = db.Column(db.String(20), nullable=True)  # Partita IVA (solo per "Consulente/P.IVA")
    hire_date = db.Column(db.Date, nullable=True)  # Data assunzione
    contract_start_date = db.Column(db.Date, nullable=True)  # Data inizio contratto
    contract_end_date = db.Column(db.Date, nullable=True)  # Data fine contratto (solo TD)
    probation_end_date = db.Column(db.Date, nullable=True)  # Fine periodo di prova
    ccnl = db.Column(db.String(100), nullable=True)  # CCNL applicato
    ccnl_level = db.Column(db.String(50), nullable=True)  # Livello contrattuale
    work_hours_week = db.Column(db.Float, nullable=True)  # Ore settimanali contratto
    working_time_type = db.Column(db.String(2), nullable=True)  # FT (Full Time) o PT (Part Time)
    part_time_percentage = db.Column(db.Float, nullable=True)  # Percentuale se PT (es. 50, 75)
    part_time_type = db.Column(db.String(20), nullable=True)  # 'Verticale' o 'Orizzontale' se PT
    mansione = db.Column(db.String(100), nullable=True)  # Mansione/ruolo
    qualifica = db.Column(db.String(100), nullable=True)  # Qualifica
    cliente = db.Column(db.String(200), nullable=True)  # Cliente assegnato
    superminimo = db.Column(db.Float, nullable=True)  # Superminimo/SM assorbibile (€)
    rimborsi_diarie = db.Column(db.Float, nullable=True)  # Rimborsi/Diarie (€)
    rischio_inail = db.Column(db.String(100), nullable=True)  # Rischio INAIL
    tipo_assunzione = db.Column(db.String(100), nullable=True)  # Tipo di assunzione
    ticket_restaurant = db.Column(db.Boolean, default=False)  # Ha ticket restaurant
    other_notes = db.Column(db.Text, nullable=True)  # Altro/Note specifiche contratto
    
    # Dati economici
    gross_salary = db.Column(db.Float, nullable=True)  # RAL (Reddito Annuo Lordo)
    net_salary = db.Column(db.Float, nullable=True)  # Netto mensile
    iban = db.Column(db.String(34), nullable=True)  # IBAN per bonifico stipendio
    payment_method = db.Column(db.String(50), nullable=True)  # Metodo pagamento (bonifico, assegno, ecc.)
    meal_vouchers_value = db.Column(db.Float, nullable=True)  # Valore buoni pasto giornalieri (€)
    fuel_card = db.Column(db.Boolean, default=False)  # Ha carta carburante aziendale
    
    # Documenti identità
    id_card_type = db.Column(db.String(50), nullable=True)  # Tipo documento (CI, Patente, ecc.)
    id_card_number = db.Column(db.String(50), nullable=True)  # Numero documento
    id_card_issue_date = db.Column(db.Date, nullable=True)  # Data rilascio
    id_card_expiry = db.Column(db.Date, nullable=True)  # Data scadenza
    id_card_issued_by = db.Column(db.String(100), nullable=True)  # Ente rilascio
    passport_number = db.Column(db.String(50), nullable=True)  # Numero passaporto
    passport_expiry = db.Column(db.Date, nullable=True)  # Scadenza passaporto
    driver_license_number = db.Column(db.String(50), nullable=True)  # Numero patente
    driver_license_type = db.Column(db.String(20), nullable=True)  # Tipo patente (A, B, C, D, E, ecc.)
    driver_license_expiry = db.Column(db.Date, nullable=True)  # Scadenza patente
    
    # Contatto emergenza
    emergency_contact_name = db.Column(db.String(100), nullable=True)  # Nome contatto emergenza
    emergency_contact_phone = db.Column(db.String(20), nullable=True)  # Telefono emergenza
    emergency_contact_relation = db.Column(db.String(50), nullable=True)  # Relazione (coniuge, genitore, ecc.)
    
    # Formazione
    education_level = db.Column(db.String(100), nullable=True)  # Titolo studio (diploma, laurea, ecc.)
    education_field = db.Column(db.String(100), nullable=True)  # Campo di studio
    
    # Altri dati
    marital_status = db.Column(db.String(50), nullable=True)  # Stato civile
    dependents_number = db.Column(db.Integer, nullable=True)  # Numero familiari a carico
    disability = db.Column(db.Boolean, default=False)  # Disabilità certificata
    disability_percentage = db.Column(db.Integer, nullable=True)  # Percentuale disabilità
    
    # Dati operativi
    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=True)  # Sede di assunzione (amministrativo/contrattuale)
    aci_vehicle_id = db.Column(db.Integer, db.ForeignKey('aci_table.id'), nullable=True)  # Veicolo ACI per rimborsi km
    vehicle_registration_document = db.Column(db.String(255), nullable=True)  # Path del libretto di circolazione caricato
    overtime_enabled = db.Column(db.Boolean, default=False)  # Abilitazione straordinari
    overtime_type = db.Column(db.String(50), nullable=True)  # "Straordinario Pagato" o "Banca Ore"
    banca_ore_limite_max = db.Column(db.Float, default=40.0)  # Limite massimo ore accumulabili (solo per Banca Ore)
    banca_ore_periodo_mesi = db.Column(db.Integer, default=12)  # Periodo mesi per usufruire ore (solo per Banca Ore)
    
    # Sicurezza e requisiti
    minimum_requirements = db.Column(db.String(50), nullable=True)  # Possesso requisiti minimi (SI/NO/DA FORMARE)
    
    # Visite mediche e formazione obbligatoria
    medical_visit_date = db.Column(db.Date, nullable=True)  # Data ultima visita medica
    medical_visit_expiry = db.Column(db.Date, nullable=True)  # Scadenza visita medica
    training_general_date = db.Column(db.Date, nullable=True)  # Formazione generale (art.36-37) - data
    training_general_expiry = db.Column(db.Date, nullable=True)  # Formazione generale - scadenza (5 anni)
    training_rspp_date = db.Column(db.Date, nullable=True)  # Formazione RSPP - data
    training_rspp_expiry = db.Column(db.Date, nullable=True)  # Formazione RSPP - scadenza (5 anni)
    training_rls_date = db.Column(db.Date, nullable=True)  # Formazione RLS - data
    training_rls_expiry = db.Column(db.Date, nullable=True)  # Formazione RLS - scadenza (annuale)
    training_first_aid_date = db.Column(db.Date, nullable=True)  # Formazione primo soccorso - data
    training_first_aid_expiry = db.Column(db.Date, nullable=True)  # Formazione primo soccorso - scadenza (3 anni)
    training_emergency_date = db.Column(db.Date, nullable=True)  # Formazione emergenza - data
    training_emergency_expiry = db.Column(db.Date, nullable=True)  # Formazione emergenza - scadenza (3 anni)
    training_supervisor_date = db.Column(db.Date, nullable=True)  # Formazione preposto - data
    training_supervisor_expiry = db.Column(db.Date, nullable=True)  # Formazione preposto - scadenza (2 anni)
    
    # Note HR
    notes = db.Column(db.Text, nullable=True)  # Note interne HR
    
    # Metadata
    created_at = db.Column(db.DateTime, default=italian_now)
    updated_at = db.Column(db.DateTime, default=italian_now, onupdate=italian_now)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)  # Multi-tenant
    
    # Relationships
    user = db.relationship('User', backref=db.backref('hr_data', uselist=False, lazy=True))
    company = db.relationship('Company', backref='hr_data_records')
    sede = db.relationship('Sede', foreign_keys=[sede_id], backref='hr_employees')
    aci_vehicle = db.relationship('ACITable', foreign_keys=[aci_vehicle_id], backref='hr_assigned_users')
    
    def __repr__(self):
        return f'<UserHRData {self.matricola} - {self.user.get_full_name() if self.user else "N/A"}>'
    
    def get_age(self):
        """Calcola l'età dell'utente"""
        if not self.birth_date:
            return None
        today = date.today()
        return today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
    
    def is_contract_active(self):
        """Verifica se il contratto è attivo"""
        if not self.contract_start_date:
            return False
        today = date.today()
        if self.contract_start_date > today:
            return False
        if self.contract_end_date and self.contract_end_date < today:
            return False
        return True
    
    def is_probation_period(self):
        """Verifica se l'utente è in periodo di prova"""
        if not self.probation_end_date:
            return False
        return date.today() <= self.probation_end_date
    
    def days_until_contract_end(self):
        """Giorni rimanenti al termine del contratto (solo TD)"""
        if not self.contract_end_date:
            return None
        days = (self.contract_end_date - date.today()).days
        return days if days >= 0 else 0
    
    def is_document_expiring_soon(self, days=30):
        """Verifica se documenti sono in scadenza"""
        expiring = []
        today = date.today()
        
        if self.id_card_expiry and (self.id_card_expiry - today).days <= days:
            expiring.append(f'Documento identità (scade il {self.id_card_expiry.strftime("%d/%m/%Y")})')
        if self.passport_expiry and (self.passport_expiry - today).days <= days:
            expiring.append(f'Passaporto (scade il {self.passport_expiry.strftime("%d/%m/%Y")})')
        if self.driver_license_expiry and (self.driver_license_expiry - today).days <= days:
            expiring.append(f'Patente (scade il {self.driver_license_expiry.strftime("%d/%m/%Y")})')
        
        return expiring
    
    def get_training_expiring_soon(self, days=60):
        """Verifica se formazioni/visite sono in scadenza"""
        expiring = []
        today = date.today()
        
        if self.medical_visit_expiry and (self.medical_visit_expiry - today).days <= days:
            expiring.append(f'Visita medica (scade il {self.medical_visit_expiry.strftime("%d/%m/%Y")})')
        if self.training_general_expiry and (self.training_general_expiry - today).days <= days:
            expiring.append(f'Formazione generale (scade il {self.training_general_expiry.strftime("%d/%m/%Y")})')
        if self.training_rspp_expiry and (self.training_rspp_expiry - today).days <= days:
            expiring.append(f'Formazione RSPP (scade il {self.training_rspp_expiry.strftime("%d/%m/%Y")})')
        if self.training_rls_expiry and (self.training_rls_expiry - today).days <= days:
            expiring.append(f'Formazione RLS (scade il {self.training_rls_expiry.strftime("%d/%m/%Y")})')
        if self.training_first_aid_expiry and (self.training_first_aid_expiry - today).days <= days:
            expiring.append(f'Primo soccorso (scade il {self.training_first_aid_expiry.strftime("%d/%m/%Y")})')
        if self.training_emergency_expiry and (self.training_emergency_expiry - today).days <= days:
            expiring.append(f'Formazione emergenza (scade il {self.training_emergency_expiry.strftime("%d/%m/%Y")})')
        if self.training_supervisor_expiry and (self.training_supervisor_expiry - today).days <= days:
            expiring.append(f'Formazione preposto (scade il {self.training_supervisor_expiry.strftime("%d/%m/%Y")})')
        
        return expiring


# =============================================================================
# ATTENDANCE & TIME TRACKING MODELS
# =============================================================================

class AttendanceEvent(db.Model):
    """Modello per registrare eventi multipli di entrata/uscita nella stessa giornata"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    event_type = db.Column(db.String(20), nullable=False)  # 'clock_in', 'clock_out', 'break_start', 'break_end'
    timestamp = db.Column(db.DateTime, nullable=False)
    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=True)  # Sede dove è avvenuto l'evento
    notes = db.Column(db.Text)
    shift_status = db.Column(db.String(20), nullable=True)  # 'anticipo', 'normale', 'ritardo' per entrate/uscite
    created_at = db.Column(db.DateTime, default=italian_now)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)  # Multi-tenant
    is_manual = db.Column(db.Boolean, default=False, nullable=False)  # Indica se inserito manualmente a posteriori
    entry_type = db.Column(db.String(20), default='standard', nullable=False)  # 'standard', 'business_trip', 'other'
    
    user = db.relationship('User', backref='attendance_events')
    sede = db.relationship('Sede', backref='sede_attendance_events')
    
    @property
    def timestamp_italian(self):
        """Restituisce il timestamp convertito da UTC a ora italiana
        
        NOTA: I timestamp sono salvati come naive datetime in UTC nel database.
        Questa property li converte a Italian time per la visualizzazione.
        """
        if self.timestamp is None:
            return None
        
        # Il timestamp è salvato come naive datetime in UTC
        # Lo rendiamo timezone-aware in UTC e poi convertiamo a Italian time
        italy_tz = ZoneInfo('Europe/Rome')
        from datetime import timezone
        
        # Se il timestamp è naive, assumiamo che sia UTC
        if self.timestamp.tzinfo is None:
            utc_time = self.timestamp.replace(tzinfo=timezone.utc)
        else:
            utc_time = self.timestamp
        
        # Converti a Italian time
        italian_time = utc_time.astimezone(italy_tz)
        return italian_time
    
    @staticmethod
    def get_user_status(user_id, target_date=None):
        """Restituisce lo stato attuale dell'utente (dentro/fuori/in pausa)"""
        if target_date is None:
            target_date = date.today()
        
        # Get user's company_id to filter events correctly
        user = User.query.get(user_id)
        if not user:
            return 'out', None
        
        # Query events with proper company_id filtering
        events = AttendanceEvent.query.filter(
            AttendanceEvent.user_id == user_id,
            AttendanceEvent.company_id == user.company_id,
            AttendanceEvent.date == target_date
        ).order_by(AttendanceEvent.timestamp).all()
        
        status = 'out'  # Stato iniziale: fuori
        last_event = None
        
        for event in events:
            # Non modificare l'oggetto event direttamente per evitare problemi SQLAlchemy
            italian_timestamp = convert_to_italian_time(event.timestamp)
            
            if event.event_type == 'clock_in':
                status = 'in'
            elif event.event_type == 'clock_out':
                status = 'out'
            elif event.event_type == 'break_start':
                status = 'break'
            elif event.event_type == 'break_end':
                status = 'in'
            last_event = event
            
        return status, last_event
    
    @staticmethod
    def can_perform_action(user_id, action_type, target_date=None):
        """Verifica se l'utente può eseguire una determinata azione"""
        status, _ = AttendanceEvent.get_user_status(user_id, target_date)
        
        valid_transitions = {
            'clock_in': ['out'],
            'clock_out': ['in', 'break'],
            'break_start': ['in'],
            'break_end': ['break']
        }
        
        return status in valid_transitions.get(action_type, [])
    
    @staticmethod
    def get_daily_work_hours(user_id, target_date=None):
        """Calcola le ore lavorate totali per la giornata sommando tutte le sessioni di lavoro separate"""
        if target_date is None:
            target_date = date.today()
        
        try:
            # Get user's company_id to filter events correctly
            user = User.query.get(user_id)
            if not user:
                return 0
            
            # Use SQLAlchemy ORM with multi-tenant filtering
            # IMPORTANT: Use db.func.date() on timestamp instead of date field
            # because date field may contain incorrect values
            db_events = AttendanceEvent.query.filter(
                AttendanceEvent.user_id == user_id,
                AttendanceEvent.company_id == user.company_id,
                db.func.date(AttendanceEvent.timestamp) == target_date
            ).order_by(AttendanceEvent.timestamp).all()
            
            events = []
            for event in db_events:
                events.append({
                    'event_type': event.event_type,
                    'timestamp': event.timestamp
                })
            
            if not events:
                return 0
        except Exception as e:
            # Log error and return 0 hours if query fails
            import traceback
            traceback.print_exc()
            return 0
        
        # Prepara lista con timestamp convertiti (ora i dati sono già dictionary)
        converted_events = []
        for event in events:
            # Assicurati che il timestamp sia un datetime object
            if isinstance(event['timestamp'], str):
                timestamp = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
            else:
                timestamp = event['timestamp']
            
            converted_events.append({
                'event_type': event['event_type'],
                'timestamp': convert_to_italian_time(timestamp)
            })
        
        total_work_seconds = 0
        current_session_start = None
        break_start = None
        break_duration = 0
        
        for event in converted_events:
            if event['event_type'] == 'clock_in':
                if current_session_start is None:
                    current_session_start = event['timestamp']
                    break_duration = 0  # Reset break duration for new session
                    
            elif event['event_type'] == 'clock_out':
                if current_session_start is not None:
                    # Calcola durata sessione meno pause
                    session_duration_seconds = (event['timestamp'] - current_session_start).total_seconds()
                    
                    # Converti tutto ai minuti con arrotondamento matematico corretto
                    session_duration_minutes = round(session_duration_seconds / 60)
                    break_duration_minutes = round(break_duration / 60)
                    
                    work_minutes = max(0, session_duration_minutes - break_duration_minutes)
                    total_work_seconds += work_minutes * 60
                    
                    # Reset per prossima sessione
                    current_session_start = None
                    break_duration = 0
                    
            elif event['event_type'] == 'break_start':
                if current_session_start is not None:
                    break_start = event['timestamp']
                    
            elif event['event_type'] == 'break_end':
                if break_start is not None and current_session_start is not None:
                    # Aggiungi durata pausa alla sessione corrente
                    break_seconds = (event['timestamp'] - break_start).total_seconds()
                    break_minutes = round(break_seconds / 60)
                    break_duration += break_minutes * 60
                    break_start = None
        
        # Se c'è una sessione in corso (solo per oggi)
        if current_session_start and target_date == date.today():
            from zoneinfo import ZoneInfo
            italy_tz = ZoneInfo('Europe/Rome')
            current_time = datetime.now(italy_tz)
            
            # Se c'è una pausa in corso, aggiungila alla durata pause
            ongoing_break = 0
            if break_start:
                ongoing_break = (current_time - break_start).total_seconds()
                
            # Calcola tempo sessione corrente
            session_duration_seconds = (current_time - current_session_start).total_seconds()
            session_duration_minutes = round(session_duration_seconds / 60)
            break_duration_minutes = round(break_duration / 60)
            ongoing_break_minutes = round(ongoing_break / 60)
            
            work_minutes = max(0, session_duration_minutes - break_duration_minutes - ongoing_break_minutes)
            total_work_seconds += work_minutes * 60
        
        # Converti secondi in ore mantenendo precisione ai minuti
        # Tronca ai minuti: total_work_seconds è già in incrementi di 60 secondi
        work_hours = total_work_seconds / 3600
        
        # Non può essere negativo
        return max(0, work_hours)
    
    @staticmethod
    def get_daily_events(user_id, target_date=None):
        """Restituisce tutti gli eventi della giornata ordinati per timestamp"""
        if target_date is None:
            target_date = date.today()
        
        # Get user's company_id to filter events correctly
        user = User.query.get(user_id)
        if not user:
            return []
        
        # Query events with proper company_id filtering
        # IMPORTANT: Use db.func.date() on timestamp instead of date field
        # because date field may contain incorrect values
        events = AttendanceEvent.query.filter(
            AttendanceEvent.user_id == user_id,
            AttendanceEvent.company_id == user.company_id,
            db.func.date(AttendanceEvent.timestamp) == target_date
        ).order_by(AttendanceEvent.timestamp).all()
        
        # Restituisci eventi direttamente - i timestamp sono già in orario italiano
        return events
    
    @staticmethod
    def get_daily_summary(user_id, target_date):
        """Crea un riassunto giornaliero compatibile con la visualizzazione storica"""
        events = AttendanceEvent.get_daily_events(user_id, target_date)
        
        if not events:
            return None
            
        # Trova primo clock_in e ultimo clock_out del giorno
        first_clock_in = None
        last_clock_out = None
        first_break_start = None
        last_break_end = None
        
        for event in events:
            if event.event_type == 'clock_in' and first_clock_in is None:
                first_clock_in = event.timestamp
            elif event.event_type == 'clock_out':
                last_clock_out = event.timestamp
            elif event.event_type == 'break_start' and first_break_start is None:
                first_break_start = event.timestamp
            elif event.event_type == 'break_end':
                last_break_end = event.timestamp
        
        # Crea un oggetto simile ad AttendanceRecord per compatibilità
        class DailySummary:
            def __init__(self, date, clock_in, clock_out, break_start, break_end, user_id):
                self.date = date
                self.clock_in = clock_in
                self.clock_out = clock_out
                self.break_start = break_start
                self.break_end = break_end
                self.user_id = user_id
                self.notes = events[-1].notes if events and events[-1].notes else None
            
            def get_work_hours(self):
                return AttendanceEvent.get_daily_work_hours(self.user_id, self.date)
            
            @property
            def total_hours(self):
                """Calcola le ore totali lavorate"""
                if not self.clock_in or not self.clock_out:
                    return 0.0
                
                # Calcola la differenza in ore
                time_diff = self.clock_out - self.clock_in
                total_hours = time_diff.total_seconds() / 3600
                
                # Sottrai il tempo di pausa se presente
                if self.break_start and self.break_end:
                    break_time = self.break_end - self.break_start
                    break_hours = break_time.total_seconds() / 3600
                    total_hours -= break_hours
                
                return max(0.0, total_hours)
            
            def get_attendance_indicators(self):
                """Restituisce gli indicatori di ritardo/anticipo per entrata e uscita"""
                from utils import check_user_schedule_with_permissions
                
                indicators = {'entry': None, 'exit': None}
                
                if not self.clock_in:
                    return indicators
                
                # Controlla lo stato dell'entrata
                check_result = check_user_schedule_with_permissions(self.user_id, self.clock_in)
                if check_result['has_schedule']:
                    indicators['entry'] = check_result['entry_status']
                
                # Controlla lo stato dell'uscita se presente
                if self.clock_out:
                    check_result = check_user_schedule_with_permissions(self.user_id, self.clock_out)
                    if check_result['has_schedule']:
                        indicators['exit'] = check_result['exit_status']
                
                return indicators
        
        return DailySummary(
            date=target_date,
            clock_in=first_clock_in,
            clock_out=last_clock_out,
            break_start=first_break_start,
            break_end=last_break_end,
            user_id=user_id
        )
    
    @staticmethod
    def get_date_range_summaries(user_id, start_date, end_date):
        """Restituisce riassunti giornalieri per un range di date"""
        summaries = []
        current_date = start_date
        
        while current_date <= end_date:
            summary = AttendanceEvent.get_daily_summary(user_id, current_date)
            if summary:
                summaries.append(summary)
            current_date += timedelta(days=1)
        
        return sorted(summaries, key=lambda x: x.date, reverse=True)
    
    @staticmethod
    def calculate_status_from_events(events_list):
        """Calcola lo stato dell'utente da una lista di eventi pre-caricati"""
        if not events_list:
            return 'out', None
        
        status = 'out'
        last_event = None
        
        for event in events_list:
            if event.event_type == 'clock_in':
                status = 'in'
            elif event.event_type == 'clock_out':
                status = 'out'
            elif event.event_type == 'break_start':
                status = 'break'
            elif event.event_type == 'break_end':
                status = 'in'
            last_event = event
        
        return status, last_event
    
    @staticmethod 
    def calculate_summary_from_events(events_list):
        """Crea summary da lista di eventi pre-caricati"""
        if not events_list:
            return None
        
        first_clock_in = None
        last_clock_out = None
        first_break_start = None
        last_break_end = None
        
        for event in events_list:
            if event.event_type == 'clock_in' and first_clock_in is None:
                first_clock_in = event.timestamp
            elif event.event_type == 'clock_out':
                last_clock_out = event.timestamp
            elif event.event_type == 'break_start' and first_break_start is None:
                first_break_start = event.timestamp
            elif event.event_type == 'break_end':
                last_break_end = event.timestamp
        
        if not first_clock_in:
            return None
            
        # Usa la classe DailySummary definita sopra
        return type('DailySummary', (), {
            'date': events_list[0].date,
            'clock_in': first_clock_in,
            'clock_out': last_clock_out,
            'break_start': first_break_start,
            'break_end': last_break_end,
            'user_id': events_list[0].user_id,
            'notes': events_list[-1].notes if events_list and events_list[-1].notes else None,
            'total_hours': (last_clock_out - first_clock_in).total_seconds() / 3600 if first_clock_in and last_clock_out else 0.0
        })()
    
    @staticmethod
    def get_events_as_records(user_id, start_date, end_date):
        """Converte gli eventi in UN SOLO record per giorno per evitare duplicati"""
        from utils_tenant import filter_by_company
        # IMPORTANT: Use db.func.date() on timestamp instead of date field
        # because date field may contain incorrect values
        events = filter_by_company(AttendanceEvent.query).filter(
            AttendanceEvent.user_id == user_id,
            db.func.date(AttendanceEvent.timestamp) >= start_date,
            db.func.date(AttendanceEvent.timestamp) <= end_date
        ).order_by(AttendanceEvent.timestamp.asc()).all()
        
        # Raggruppa eventi per data estratta dal timestamp
        events_by_date = {}
        for event in events:
            # Extract date from timestamp, not from date field
            event_date = event.timestamp.date() if event.timestamp else event.date
            if event_date not in events_by_date:
                events_by_date[event_date] = []
            events_by_date[event_date].append(event)
        
        records = []
        
        # Per ogni giorno, crea UN SOLO record con primo clock_in e ultimo clock_out
        for date, day_events in events_by_date.items():
            if not day_events:
                continue
                
            # Trova primo clock_in e ultimo clock_out del giorno
            first_clock_in = None
            last_clock_out = None
            first_break_start = None
            last_break_end = None
            all_notes = []
            
            for event in day_events:
                if event.event_type == 'clock_in' and first_clock_in is None:
                    first_clock_in = event.timestamp
                elif event.event_type == 'clock_out':
                    last_clock_out = event.timestamp
                elif event.event_type == 'break_start' and first_break_start is None:
                    first_break_start = event.timestamp
                elif event.event_type == 'break_end':
                    last_break_end = event.timestamp
                
                if event.notes:
                    all_notes.append(event.notes)
            
            # Crea UN SOLO record per giorno
            class DayRecord:
                def __init__(self, date, clock_in=None, clock_out=None, break_start=None, break_end=None, notes=None, user=None):
                    self.date = date
                    self.clock_in = clock_in
                    self.clock_out = clock_out
                    self.break_start = break_start
                    self.break_end = break_end
                    self.notes = notes or ""
                    self.user_id = user_id
                    self.user = user
                
                def get_work_hours(self):
                    return AttendanceEvent.get_daily_work_hours(self.user_id, self.date)
                
                def get_attendance_indicators(self):
                    """Restituisce gli indicatori di ritardo/anticipo per entrata e uscita"""
                    from utils import check_user_schedule_with_permissions
                    
                    indicators = {'entry': None, 'exit': None}
                    
                    if not self.clock_in:
                        return indicators
                    
                    # Controlla lo stato dell'entrata
                    check_result = check_user_schedule_with_permissions(self.user_id, self.clock_in)
                    if check_result['has_schedule']:
                        indicators['entry'] = check_result['entry_status']
                    
                    # Controlla lo stato dell'uscita se presente
                    if self.clock_out:
                        check_result = check_user_schedule_with_permissions(self.user_id, self.clock_out)
                        if check_result['has_schedule']:
                            indicators['exit'] = check_result['exit_status']
                    
                    return indicators
            
            # Ottieni informazioni utente dal primo evento del giorno
            user = day_events[0].user if day_events else None
            
            records.append(DayRecord(
                date=date,
                clock_in=first_clock_in,
                clock_out=last_clock_out,
                break_start=first_break_start,
                break_end=last_break_end,
                notes=' | '.join(all_notes) if all_notes else '',
                user=user
            ))
        
        # Ordina per data decrescente
        records.sort(key=lambda x: x.date, reverse=True)
        return records
    
    @staticmethod
    def create_work_sequences(day_events):
        """Crea sequenze di lavoro (entrata-uscita) da una lista di eventi"""
        sequences = []
        current_seq = {}
        
        for event in day_events:
            if event.event_type == 'clock_in':
                # Inizia una nuova sequenza
                if current_seq:  # Se c'era una sequenza precedente senza clock_out
                    sequences.append(current_seq)
                current_seq = {
                    'clock_in': event.timestamp,
                    'notes': event.notes or ''
                }
            elif event.event_type == 'clock_out':
                if current_seq:  # Se c'è una sequenza attiva
                    current_seq['clock_out'] = event.timestamp
                    if event.notes:
                        current_seq['notes'] += (' ' + event.notes if current_seq['notes'] else event.notes)
                    sequences.append(current_seq)
                    current_seq = {}
                else:
                    # Clock out senza clock in precedente - solo se ha timestamp valido
                    if event.timestamp:
                        sequences.append({
                            'clock_out': event.timestamp,
                            'notes': event.notes or ''
                        })
            elif event.event_type == 'break_start':
                if current_seq:
                    current_seq['break_start'] = event.timestamp
                    if event.notes:
                        current_seq['notes'] += (' ' + event.notes if current_seq['notes'] else event.notes)
            elif event.event_type == 'break_end':
                if current_seq:
                    current_seq['break_end'] = event.timestamp
                    if event.notes:
                        current_seq['notes'] += (' ' + event.notes if current_seq['notes'] else event.notes)
        
        # Aggiungi l'ultima sequenza se incompleta e ha almeno un timestamp
        if current_seq and (current_seq.get('clock_in') or current_seq.get('clock_out')):
            sequences.append(current_seq)
        
        # Filtra sequenze che hanno almeno un timestamp valido
        valid_sequences = []
        for seq in sequences:
            if seq.get('clock_in') or seq.get('clock_out') or seq.get('break_start') or seq.get('break_end'):
                valid_sequences.append(seq)
        
        # Se non ci sono sequenze valide, non creare righe vuote
        return valid_sequences if valid_sequences else []
    
    @staticmethod
    def validate_data_integrity(user_id=None, date_range_days=7):
        """Identifica incongruenze nei dati di presenza (clock_in senza clock_out, etc.)"""
        from datetime import date, timedelta
        from utils_tenant import filter_by_company
        
        query = filter_by_company(AttendanceEvent.query)
        if user_id:
            query = query.filter(AttendanceEvent.user_id == user_id)
        
        # Controlla ultimi N giorni se non specificato diversamente
        end_date = date.today()
        start_date = end_date - timedelta(days=date_range_days)
        query = query.filter(AttendanceEvent.date >= start_date, AttendanceEvent.date <= end_date)
        
        events = query.order_by(AttendanceEvent.date.asc(), AttendanceEvent.timestamp.asc()).all()
        
        issues = []
        events_by_user_date = {}
        
        # Raggruppa eventi per utente e data
        for event in events:
            key = (event.user_id, event.date)
            if key not in events_by_user_date:
                events_by_user_date[key] = []
            events_by_user_date[key].append(event)
        
        # Controlla ogni giorno per ogni utente
        for (user_id, date_check), day_events in events_by_user_date.items():
            clock_ins = [e for e in day_events if e.event_type == 'clock_in']
            clock_outs = [e for e in day_events if e.event_type == 'clock_out']
            break_starts = [e for e in day_events if e.event_type == 'break_start']
            break_ends = [e for e in day_events if e.event_type == 'break_end']
            
            # Controlla incongruenze
            if len(clock_ins) != len(clock_outs):
                issues.append({
                    'type': 'unmatched_clock_events',
                    'user_id': user_id,
                    'date': date_check,
                    'description': f'Clock-in: {len(clock_ins)}, Clock-out: {len(clock_outs)}',
                    'severity': 'high'
                })
            
            if len(break_starts) != len(break_ends):
                issues.append({
                    'type': 'unmatched_break_events',
                    'user_id': user_id,
                    'date': date_check,
                    'description': f'Break-start: {len(break_starts)}, Break-end: {len(break_ends)}',
                    'severity': 'medium'
                })
        
        return issues


# =============================================================================
# ATTENDANCE EVENT TIMEZONE NORMALIZATION
# =============================================================================

from sqlalchemy import event

@event.listens_for(AttendanceEvent.timestamp, 'set', retval=True)
def normalize_attendance_timestamp(target, value, oldvalue, initiator):
    """
    Normalizza automaticamente tutti i timestamp AttendanceEvent in UTC naive.
    
    Questo listener viene chiamato automaticamente prima di salvare un AttendanceEvent.
    Converte qualsiasi datetime timezone-aware in naive UTC per garantire consistenza.
    
    Esempi:
    - Input: 18:15+02:00 (Italian time) → Output: 16:15 (naive UTC)
    - Input: 16:15+00:00 (UTC) → Output: 16:15 (naive UTC)
    - Input: 16:15 (naive, assume UTC) → Output: 16:15 (naive UTC)
    """
    if value is None:
        return value
    
    from datetime import timezone
    
    # Se il timestamp ha timezone info, convertilo in UTC e rimuovi il timezone
    if value.tzinfo is not None:
        # Converti a UTC
        utc_time = value.astimezone(timezone.utc)
        # Ritorna come naive datetime (rimuovi timezone info)
        return utc_time.replace(tzinfo=None)
    
    # Se il timestamp è già naive, assumiamo sia già UTC
    return value


class MonthlyTimesheet(db.Model):
    """Modello per gestire lo stato di consolidamento del timesheet mensile"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)  # 1-12
    is_consolidated = db.Column(db.Boolean, default=False, nullable=False)
    consolidated_at = db.Column(db.DateTime, nullable=True)
    consolidated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=italian_now)
    updated_at = db.Column(db.DateTime, default=italian_now, onupdate=italian_now)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)
    
    user = db.relationship('User', foreign_keys=[user_id], backref='monthly_timesheets')
    consolidator = db.relationship('User', foreign_keys=[consolidated_by])
    
    def __repr__(self):
        return f'<MonthlyTimesheet {self.user_id} {self.year}-{self.month:02d}>'
    
    @staticmethod
    def get_or_create(user_id, year, month, company_id):
        """Ottieni o crea un timesheet mensile"""
        timesheet = MonthlyTimesheet.query.filter_by(
            user_id=user_id,
            year=year,
            month=month,
            company_id=company_id
        ).first()
        
        if not timesheet:
            timesheet = MonthlyTimesheet(
                user_id=user_id,
                year=year,
                month=month,
                company_id=company_id
            )
            db.session.add(timesheet)
            db.session.commit()
        
        return timesheet
    
    def can_edit(self):
        """Verifica se il timesheet può essere modificato"""
        return not self.is_consolidated
    
    def consolidate(self, consolidator_id):
        """Consolida il timesheet rendendolo immutabile"""
        if not self.is_consolidated:
            self.is_consolidated = True
            self.consolidated_at = italian_now()
            self.consolidated_by = consolidator_id
            db.session.commit()
            return True
        return False

# =============================================================================
# LEAVE MANAGEMENT MODELS
# =============================================================================

class LeaveType(db.Model):
    """Modello per la gestione delle tipologie di permesso configurabili dall'amministratore"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    requires_approval = db.Column(db.Boolean, default=True)  # Se richiede autorizzazione
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=italian_now)
    updated_at = db.Column(db.DateTime, default=italian_now, onupdate=italian_now)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)  # Multi-tenant
    
    # Nota: la relazione è definita in LeaveRequest con backref='requests'
    
    def __repr__(self):
        return f'<LeaveType {self.name}>'
    
    @classmethod
    def get_default_types(cls):
        """Restituisce le tipologie di permesso predefinite per l'inizializzazione"""
        return [
            {'name': 'Ferie', 'description': 'Giorni di ferie annuali', 'requires_approval': True},
            {'name': 'Permesso retribuito', 'description': 'Permesso retribuito per necessità personali', 'requires_approval': True},
            {'name': 'Permesso non retribuito', 'description': 'Permesso non retribuito per necessità personali', 'requires_approval': True},
            {'name': 'Permesso per malattia del dipendente', 'description': 'Assenza per malattia del dipendente', 'requires_approval': False},
            {'name': 'Permesso per assistenza a familiari (104)', 'description': 'Permesso ex legge 104 per assistenza familiari', 'requires_approval': True},
            {'name': 'Permesso per studio', 'description': 'Permesso per motivi di studio', 'requires_approval': True},
            {'name': 'Permesso per partecipazione a corsi di formazione', 'description': 'Permesso per formazione volontaria', 'requires_approval': True},
            {'name': 'Permesso per partecipazione a corsi di formazione obbligatori', 'description': 'Permesso per formazione obbligatoria aziendale', 'requires_approval': False}
        ]

class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    leave_type_id = db.Column(db.Integer, db.ForeignKey('leave_type.id'), nullable=True)  # Riferimento alla tipologia (nullable per migrazione)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    leave_type = db.Column(db.String(50), nullable=True)  # Manteniamo per retrocompatibilità, sarà deprecato
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='Pending')  # Pending, Approved, Rejected
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=italian_now)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)  # Multi-tenant
    
    # Campi per permessi orari
    start_time = db.Column(db.Time, nullable=True)  # Orario inizio per permessi parziali
    end_time = db.Column(db.Time, nullable=True)    # Orario fine per permessi parziali
    
    # Campo per banca ore
    use_banca_ore = db.Column(db.Boolean, default=False)  # True se utilizza ore dalla banca ore
    banca_ore_hours_used = db.Column(db.Float, nullable=True)  # Ore effettivamente utilizzate dalla banca ore
    
    user = db.relationship('User', foreign_keys=[user_id], backref='leave_requests')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_leaves')
    leave_type_obj = db.relationship('LeaveType', foreign_keys=[leave_type_id], backref='requests')
    
    def is_time_based(self):
        """Verifica se il permesso è basato su orari (permessi parziali)"""
        return self.start_time is not None and self.end_time is not None
    
    def get_duration_display(self):
        """Restituisce la durata del permesso in formato leggibile"""
        if self.is_time_based():
            # Calcola la durata in ore
            start_dt = datetime.combine(date.today(), self.start_time)
            end_dt = datetime.combine(date.today(), self.end_time)
            if end_dt < start_dt:  # Attraversa mezzanotte
                end_dt += timedelta(days=1)
            duration = end_dt - start_dt
            hours = duration.total_seconds() / 3600
            return f"{hours:.1f}h ({self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')})"
        else:
            # Permesso giornaliero intero
            if self.start_date == self.end_date:
                return "Giornata intera"
            else:
                days = (self.end_date - self.start_date).days + 1
                return f"{days} giorni"
    
    def get_leave_type_name(self):
        """Restituisce il nome della tipologia di permesso"""
        if self.leave_type_obj:
            return self.leave_type_obj.name
        # Fallback per retrocompatibilità
        return self.leave_type or 'Tipo non specificato'
    
    def requires_approval(self):
        """Verifica se il permesso richiede approvazione"""
        if self.leave_type_obj:
            return self.leave_type_obj.requires_approval
        # Fallback: malattia non richiede approvazione, resto sì
        return self.leave_type != 'Malattia' if self.leave_type else True
    
    def get_duration_hours(self):
        """Calcola la durata del permesso in ore"""
        if self.is_time_based():
            # Permesso orario
            start_dt = datetime.combine(date.today(), self.start_time)
            end_dt = datetime.combine(date.today(), self.end_time)
            if end_dt < start_dt:  # Attraversa mezzanotte
                end_dt += timedelta(days=1)
            duration = end_dt - start_dt
            return round(duration.total_seconds() / 3600, 2)
        else:
            # Permesso giornaliero intero - assumiamo 8 ore per giorno
            days = (self.end_date - self.start_date).days + 1
            return days * 8.0
    
    def can_use_banca_ore(self):
        """Verifica se questa richiesta può utilizzare ore dalla banca ore"""
        return (self.user and self.user.overtime_enabled and 
                self.user.overtime_type == 'Banca Ore' and 
                self.is_time_based())  # Solo permessi orari possono usare banca ore
    
    def calculate_banca_ore_hours_needed(self):
        """Calcola le ore necessarie dalla banca ore per questo permesso"""
        if not self.can_use_banca_ore():
            return 0.0
        return self.get_duration_hours()
    
    def get_banca_ore_display(self):
        """Restituisce info display per banca ore"""
        if self.use_banca_ore and self.banca_ore_hours_used:
            return f"Banca Ore: {self.banca_ore_hours_used:.1f}h utilizzate"
        elif self.use_banca_ore:
            needed = self.calculate_banca_ore_hours_needed()
            return f"Banca Ore: {needed:.1f}h richieste"
        return None

# =============================================================================
# SHIFT MANAGEMENT MODELS  
# =============================================================================

class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    shift_type = db.Column(db.String(50), nullable=False, default='Turno')  # Simplified shift type
    created_at = db.Column(db.DateTime, default=italian_now)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)  # Multi-tenant
    
    user = db.relationship('User', foreign_keys=[user_id], backref='shifts')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_shifts')
    
    def get_duration_hours(self):
        from datetime import datetime, timedelta
        start_dt = datetime.combine(date.today(), self.start_time)
        end_dt = datetime.combine(date.today(), self.end_time)
        if end_dt < start_dt:  # Next day
            end_dt += timedelta(days=1)
        return (end_dt - start_dt).total_seconds() / 3600

class ShiftTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=italian_now)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)  # Multi-tenant
    
    creator = db.relationship('User', backref='shift_templates')


class PresidioCoverageTemplate(db.Model):
    """Template di copertura presidio con nome e periodo di validità"""
    __tablename__ = 'presidio_coverage_template'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Nome del template
    start_date = db.Column(db.Date, nullable=False)   # Data inizio validità
    end_date = db.Column(db.Date, nullable=False)     # Data fine validità
    description = db.Column(db.String(200))           # Descrizione opzionale
    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=True)  # Sede associata
    active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=italian_now)
    updated_at = db.Column(db.DateTime, default=italian_now, onupdate=italian_now)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)  # Multi-tenant

    # Relazioni
    creator = db.relationship('User', backref='presidio_coverage_templates')
    sede = db.relationship('Sede', backref='presidio_templates')
    coverages = db.relationship('PresidioCoverage', backref='template', lazy='dynamic', cascade='all, delete-orphan')

    def get_period_display(self):
        """Restituisce il periodo di validità formattato"""
        return f"{self.start_date.strftime('%d/%m/%Y')} - {self.end_date.strftime('%d/%m/%Y')}"
    
    def get_total_hours_per_week(self):
        """Calcola le ore totali di copertura settimanale"""
        total_hours = 0
        for coverage in self.coverages.filter_by(active=True):
            total_hours += coverage.get_duration_hours()
        return total_hours
    
    def get_covered_days_count(self):
        """Conta i giorni della settimana con copertura"""
        covered_days = set()
        for coverage in self.coverages.filter_by(active=True):
            covered_days.add(coverage.day_of_week)
        return len(covered_days)
    
    def get_involved_roles(self):
        """Restituisce tutti i ruoli coinvolti nella copertura"""
        all_roles = set()
        for coverage in self.coverages.filter_by(active=True):
            roles = coverage.get_required_roles()
            all_roles.update(roles)
        return list(all_roles)

    def __repr__(self):
        return f'<PresidioCoverageTemplate {self.name}>'

class PresidioCoverage(db.Model):
    """Definisce la copertura presidio per giorno della settimana e fascia oraria con periodo di validità"""
    __tablename__ = 'presidio_coverage'
    
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('presidio_coverage_template.id'), nullable=True)  # Nullable per backward compatibility
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Lunedì, 1=Martedì, ..., 6=Domenica
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    required_roles = db.Column(db.Text, nullable=False)  # JSON object con ruoli e numerosità: {"Operatore": 2, "Tecnico": 1}
    role_count = db.Column(db.Integer, default=1)       # Numero di persone richieste per ruolo (nuovo)
    break_start = db.Column(db.Time)                     # Ora inizio pausa (nuovo dal pacchetto)
    break_end = db.Column(db.Time)                       # Ora fine pausa (nuovo dal pacchetto)
    description = db.Column(db.String(200))  # Descrizione opzionale della copertura
    active = db.Column(db.Boolean, default=True)
    # Campi per backward compatibility - periodo di validità per coperture senza template
    start_date = db.Column(db.Date, nullable=True)  # Data inizio validità (ora nullable)
    end_date = db.Column(db.Date, nullable=True)    # Data fine validità (ora nullable)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=italian_now)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)  # Multi-tenant

    creator = db.relationship('User', backref='presidio_coverages')
    template_ref = db.relationship('PresidioCoverageTemplate', foreign_keys=[template_id], overlaps="coverages,template")

    def get_day_name(self):
        """Restituisce il nome del giorno in italiano"""
        days = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
        return days[self.day_of_week] if self.day_of_week < len(days) else 'Sconosciuto'
    
    def get_time_range(self):
        """Restituisce la fascia oraria formattata"""
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"
    
    def get_required_roles_dict(self):
        """Restituisce il dizionario ruoli e numerosità dal JSON"""
        import json
        try:
            data = json.loads(self.required_roles)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_required_roles_dict(self, roles_dict):
        """Imposta il dizionario ruoli e numerosità come JSON"""
        import json
        self.required_roles = json.dumps(roles_dict)
    
    def get_required_roles_list(self):
        """Retrocompatibilità: restituisce solo la lista dei ruoli"""
        return list(self.get_required_roles_dict().keys())
    
    def set_required_roles_list(self, roles_list):
        """Retrocompatibilità: converte lista in dizionario con count=1"""
        roles_dict = {role: 1 for role in roles_list}
        self.set_required_roles_dict(roles_dict)
    
    def get_required_roles(self):
        """Nuovo metodo dal pacchetto: restituisce la lista dei ruoli richiesti dal JSON"""
        import json
        try:
            # Prima prova formato nuovo (array)
            data = json.loads(self.required_roles)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                # Formato esistente (dizionario) - restituisci solo le chiavi
                return list(data.keys())
            return []
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_required_roles(self, roles_list):
        """Nuovo metodo dal pacchetto: imposta la lista dei ruoli richiesti come JSON"""
        import json
        self.required_roles = json.dumps(roles_list)
    
    def get_required_roles_display(self):
        """Restituisce i ruoli con numerosità formattati per la visualizzazione"""
        if not self.required_roles:
            return "Nessun ruolo"
        
        # Usa il metodo get_required_roles_dict che gestisce già la retrocompatibilità
        roles_dict = self.get_required_roles_dict()
        if not roles_dict:
            return "Nessun ruolo"
        
        role_strings = []
        for role, count in roles_dict.items():
            if count == 1:
                role_strings.append(role)
            else:
                role_strings.append(f"{count} {role}")
        
        if len(role_strings) == 1:
            return role_strings[0]
        elif len(role_strings) == 2:
            return f"{role_strings[0]} + {role_strings[1]}"
        else:
            return ", ".join(role_strings[:-1]) + f" + {role_strings[-1]}"
    
    def get_total_resources_needed(self):
        """Restituisce il numero totale di risorse necessarie"""
        roles_dict = self.get_required_roles_dict()
        return sum(roles_dict.values())
    
    def is_valid_for_date(self, check_date):
        """Verifica se la copertura è valida per una data specifica tramite il template o periodo diretto"""
        if self.template_id and self.template:
            return (self.template.start_date <= check_date <= self.template.end_date and 
                    self.active and self.template.active)
        elif self.start_date and self.end_date:
            # Backward compatibility: usa i campi diretti se non c'è template
            return self.start_date <= check_date <= self.end_date and self.active
        return self.active  # Se non ci sono date, considera solo active
    
    def get_period_display(self):
        """Restituisce il periodo di validità formattato"""
        if self.template_id and self.template:
            return self.template.get_period_display()
        elif self.start_date and self.end_date:
            return f"{self.start_date.strftime('%d/%m/%Y')} - {self.end_date.strftime('%d/%m/%Y')}"
        return "Periodo non definito"
    
    def get_break_range(self):
        """Nuovo metodo dal pacchetto: restituisce la fascia della pausa formattata"""
        if self.break_start and self.break_end:
            return f"{self.break_start.strftime('%H:%M')} - {self.break_end.strftime('%H:%M')}"
        return None
    
    def get_duration_hours(self):
        """Nuovo metodo dal pacchetto: calcola la durata in ore della copertura"""
        from datetime import datetime, timedelta
        
        # Converti time in datetime per calcolare la differenza
        start_dt = datetime.combine(datetime.today(), self.start_time)
        end_dt = datetime.combine(datetime.today(), self.end_time)
        
        # Gestisci il caso in cui end_time sia il giorno dopo (es. turno notturno)
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)
        
        duration = end_dt - start_dt
        return duration.total_seconds() / 3600  # Converti in ore
    
    def get_effective_work_hours(self):
        """Nuovo metodo dal pacchetto: calcola le ore effettive considerando la pausa"""
        total_hours = self.get_duration_hours()
        
        if self.break_start and self.break_end:
            # Calcola durata pausa
            from datetime import datetime
            break_start_dt = datetime.combine(datetime.today(), self.break_start)
            break_end_dt = datetime.combine(datetime.today(), self.break_end)
            break_duration = (break_end_dt - break_start_dt).total_seconds() / 3600
            
            total_hours -= break_duration
        
        return max(0, total_hours)  # Non può essere negativa
    
    def overlaps_with(self, other_coverage):
        """Nuovo metodo dal pacchetto: verifica se questa copertura si sovrappone con un'altra nello stesso giorno"""
        if self.day_of_week != other_coverage.day_of_week:
            return False
        
        # Controlla sovrapposizione oraria
        return not (self.end_time <= other_coverage.start_time or 
                   self.start_time >= other_coverage.end_time)

    def __repr__(self):
        return f'<PresidioCoverage {self.get_day_name()} {self.get_time_range()}>'

# Funzioni di utilità per query comuni del pacchetto presidio
def get_active_presidio_templates():
    """Ottieni tutti i template presidio attivi"""
    return PresidioCoverageTemplate.query.filter_by(active=True).order_by(
        PresidioCoverageTemplate.start_date.desc()
    ).all()

def get_presidio_coverage_for_day(day_of_week, target_date=None):
    """Ottieni coperture presidio per un giorno specifico"""
    query = PresidioCoverage.query.filter(
        PresidioCoverage.day_of_week == day_of_week,
        PresidioCoverage.active == True
    )
    
    if target_date:
        # Filtra per template validi nella data specifica
        query = query.join(PresidioCoverageTemplate).filter(
            PresidioCoverageTemplate.start_date <= target_date,
            PresidioCoverageTemplate.end_date >= target_date,
            PresidioCoverageTemplate.active == True
        )
    
    return query.order_by(PresidioCoverage.start_time).all()

def get_required_roles_for_time_slot(day_of_week, time_slot, target_date=None):
    """Ottieni ruoli richiesti per un giorno e orario specifico"""
    coverages = get_presidio_coverage_for_day(day_of_week, target_date)
    
    required_roles = set()
    for coverage in coverages:
        if coverage.start_time <= time_slot < coverage.end_time:
            required_roles.update(coverage.get_required_roles())
    
    return list(required_roles)


# =============================================================================
# REPERIBILITÀ MODELS
# =============================================================================

class ReperibilitaCoverage(db.Model):
    """Definisce la copertura reperibilità per giorno della settimana e fascia oraria con periodo di validità"""
    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Lunedì, 1=Martedì, ..., 6=Domenica, 7=Festivi
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    required_roles = db.Column(db.Text, nullable=False)  # JSON array dei ruoli richiesti per questa fascia
    sedi_ids = db.Column(db.Text, nullable=False)  # JSON array degli ID delle sedi coinvolte
    description = db.Column(db.String(200))  # Descrizione opzionale della copertura
    active = db.Column(db.Boolean, default=True)
    
    # Periodo di validità
    start_date = db.Column(db.Date, nullable=False)  # Data inizio validità
    end_date = db.Column(db.Date, nullable=False)    # Data fine validità
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=italian_now)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)  # Multi-tenant
    
    creator = db.relationship('User', backref='reperibilita_coverages')
    company = db.relationship('Company', backref='reperibilita_coverages')
    
    def get_day_name(self):
        """Restituisce il nome del giorno in italiano"""
        days = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica', 'Festivi']
        return days[self.day_of_week] if self.day_of_week < len(days) else 'Sconosciuto'
    
    def get_time_range(self):
        """Restituisce la fascia oraria formattata"""
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"
    
    def get_required_roles_list(self):
        """Restituisce la lista dei ruoli richiesti dal JSON"""
        try:
            import json
            return json.loads(self.required_roles)
        except:
            return []
    
    def set_required_roles_list(self, roles_list):
        """Imposta la lista dei ruoli richiesti come JSON"""
        import json
        self.required_roles = json.dumps(roles_list)
    
    def get_required_roles_display(self):
        """Restituisce i ruoli formattati per la visualizzazione"""
        roles = self.get_required_roles_list()
        return ', '.join(roles) if roles else 'Nessuno'
    
    def get_sedi_ids_list(self):
        """Restituisce la lista degli ID delle sedi dal JSON"""
        try:
            import json
            return [int(sid) for sid in json.loads(self.sedi_ids)]
        except:
            return []
    
    def set_sedi_ids_list(self, sedi_ids_list):
        """Imposta la lista degli ID delle sedi come JSON"""
        import json
        self.sedi_ids = json.dumps([int(sid) for sid in sedi_ids_list])
    
    def get_sedi_names(self):
        """Restituisce i nomi delle sedi coinvolte"""
        sede_ids = self.get_sedi_ids_list()
        if not sede_ids:
            return 'Nessuna sede'
        
        sedi = Sede.query.filter(Sede.id.in_(sede_ids)).all()
        return ', '.join([sede.name for sede in sedi])
    
    def get_sedi_objects(self):
        """Restituisce gli oggetti Sede coinvolti"""
        sede_ids = self.get_sedi_ids_list()
        if not sede_ids:
            return []
        
        return Sede.query.filter(Sede.id.in_(sede_ids)).all()
    
    def is_valid_for_date(self, check_date):
        """Verifica se la copertura è valida per una data specifica"""
        return self.start_date <= check_date <= self.end_date and self.active
    
    def get_period_display(self):
        """Restituisce il periodo di validità formattato"""
        return f"{self.start_date.strftime('%d/%m/%Y')} - {self.end_date.strftime('%d/%m/%Y')}"


class ReperibilitaShift(db.Model):
    """Turni di reperibilità separati dai turni normali"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    description = db.Column(db.String(200))  # Descrizione del turno reperibilità
    created_at = db.Column(db.DateTime, default=italian_now)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)  # Multi-tenant
    
    user = db.relationship('User', foreign_keys=[user_id], backref='reperibilita_shifts')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_reperibilita_shifts')
    company = db.relationship('Company', backref='reperibilita_shifts')
    
    def get_duration_hours(self):
        """Calcola la durata del turno in ore"""
        start = datetime.combine(date.today(), self.start_time)
        end = datetime.combine(date.today(), self.end_time)
        
        # Handle overnight shifts
        if end < start:
            end += timedelta(days=1)
        
        duration = end - start
        return duration.total_seconds() / 3600


class ReperibilitaIntervention(db.Model):
    """Interventi di reperibilità registrati dagli utenti"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    shift_id = db.Column(db.Integer, db.ForeignKey('reperibilita_shift.id'), nullable=True)
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=True)
    description = db.Column(db.Text, nullable=True)
    priority = db.Column(db.String(10), default='Media', nullable=False)  # 'Bassa', 'Media', 'Alta'
    is_remote = db.Column(db.Boolean, default=True, nullable=False)  # True = remoto, False = in presenza
    created_at = db.Column(db.DateTime, default=italian_now)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)  # Multi-tenant
    
    # Relationships
    user = db.relationship('User', backref='reperibilita_interventions')
    shift = db.relationship('ReperibilitaShift', backref='interventions')
    company = db.relationship('Company', backref='reperibilita_interventions')
    
    @property
    def duration_minutes(self):
        """Calcola la durata dell'intervento in minuti"""
        if self.end_datetime:
            delta = self.end_datetime - self.start_datetime
            return round(delta.total_seconds() / 60, 1)
        return None
    
    @property
    def is_active(self):
        """Controlla se l'intervento è ancora attivo (non terminato)"""
        return self.end_datetime is None
    
    def __repr__(self):
        return f'<ReperibilitaIntervention {self.user.username} at {self.start_datetime}>'


# =============================================================================
# INTERVENTION MODELS
# =============================================================================

class Intervention(db.Model):
    """Interventi generici registrati dagli utenti (non di reperibilità)"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=True)
    description = db.Column(db.Text, nullable=True)
    priority = db.Column(db.String(10), default='Media', nullable=False)  # 'Bassa', 'Media', 'Alta'
    is_remote = db.Column(db.Boolean, default=True, nullable=False)  # True = remoto, False = in presenza
    created_at = db.Column(db.DateTime, default=italian_now)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)  # Multi-tenant
    
    # Relationships
    user = db.relationship('User', backref='general_interventions')
    
    @property
    def duration_minutes(self):
        """Calcola la durata dell'intervento in minuti"""
        if self.end_datetime:
            delta = self.end_datetime - self.start_datetime
            return round(delta.total_seconds() / 60, 1)
        return None
    
    @property
    def is_active(self):
        """Controlla se l'intervento è ancora attivo (non terminato)"""
        return self.end_datetime is None
    
    def __repr__(self):
        return f'<Intervention {self.user.username} at {self.start_datetime}>'


class ReperibilitaTemplate(db.Model):
    """Template per generazione automatica turni reperibilità"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=italian_now)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)  # Multi-tenant
    
    creator = db.relationship('User', backref='reperibilita_templates')


# =============================================================================
# ADMINISTRATIVE MODELS
# =============================================================================

class Holiday(db.Model):
    """Festività gestibili dagli amministratori - nazionali e per sede"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    month = db.Column(db.Integer, nullable=False)  # 1-12
    day = db.Column(db.Integer, nullable=False)    # 1-31
    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=True)  # NULL = nazionale
    active = db.Column(db.Boolean, default=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=italian_now)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)  # Multi-tenant
    
    # Relationships
    creator = db.relationship('User', backref='created_holidays')
    sede = db.relationship('Sede', backref='holidays')
    
    def __repr__(self):
        scope = f" ({self.sede_obj.name})" if self.sede_obj else " (Nazionale)"
        return f'<Holiday {self.name}: {self.day}/{self.month}{scope}>'
    
    @property
    def date_display(self):
        """Formato visualizzazione data"""
        return f"{self.day:02d}/{self.month:02d}"
    
    @property
    def scope_display(self):
        """Visualizza l'ambito della festività"""
        return self.sede_obj.name if self.sede_obj else "Nazionale"
    
    def is_holiday_on_date(self, check_date):
        """Verifica se questa festività cade nella data specificata"""
        return (check_date.month == self.month and 
                check_date.day == self.day and 
                self.active)
    
    @classmethod
    def get_holidays_for_date(cls, check_date, sede_id=None):
        """Ottiene tutte le festività per una data specifica e sede"""
        query = cls.query.filter(
            cls.month == check_date.month,
            cls.day == check_date.day,
            cls.active == True
        )
        
        if sede_id:
            # Festività nazionali OR festività specifiche per questa sede
            query = query.filter(db.or_(
                cls.sede_id.is_(None),
                cls.sede_id == sede_id
            ))
        else:
            # Solo festività nazionali
            query = query.filter(cls.sede_id.is_(None))
        
        return query.all()


class InternalMessage(db.Model):
    """Modello per messaggi interni del sistema"""
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # None per messaggi di sistema
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(50), default='info')  # 'info', 'warning', 'success', 'danger'
    is_read = db.Column(db.Boolean, default=False)
    related_leave_request_id = db.Column(db.Integer, db.ForeignKey('leave_request.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=italian_now)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)  # Multi-tenant
    message_group_id = db.Column(db.String(36), nullable=True)  # UUID per raggruppare messaggi multipli
    
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    related_leave_request = db.relationship('LeaveRequest', backref='messages')
    
    def __repr__(self):
        return f'<InternalMessage {self.title} to {self.recipient.username}>'
    
    def get_sender_name(self):
        """Restituisce il nome del mittente o 'Sistema' se è un messaggio automatico"""
        return self.sender.get_full_name() if self.sender else 'Sistema'
    
    def get_recipient_name(self):
        """Restituisce il nome del destinatario"""
        return self.recipient.get_full_name() if self.recipient else 'Sconosciuto'
    
    def get_all_recipients(self):
        """Restituisce tutti i destinatari se il messaggio è parte di un gruppo"""
        if self.message_group_id:
            # Nuovi messaggi con group_id
            grouped_messages = InternalMessage.query.filter_by(
                message_group_id=self.message_group_id
            ).all()
            return [msg.recipient for msg in grouped_messages]
        else:
            # Messaggi vecchi senza group_id: raggruppa per sender+title+timestamp
            if self.sender_id:
                timestamp_key = self.created_at.replace(microsecond=0)
                grouped_messages = InternalMessage.query.filter_by(
                    sender_id=self.sender_id,
                    title=self.title
                ).filter(
                    db.func.date_trunc('second', InternalMessage.created_at) == timestamp_key
                ).all()
                return [msg.recipient for msg in grouped_messages]
            
            return [self.recipient]
    
    def get_recipients_count(self):
        """Restituisce il numero di destinatari per messaggi raggruppati"""
        if self.message_group_id:
            return InternalMessage.query.filter_by(
                message_group_id=self.message_group_id
            ).count()
        else:
            # Messaggi vecchi senza group_id: conta per sender+title+timestamp
            if self.sender_id:
                timestamp_key = self.created_at.replace(microsecond=0)
                return InternalMessage.query.filter_by(
                    sender_id=self.sender_id,
                    title=self.title
                ).filter(
                    db.func.date_trunc('second', InternalMessage.created_at) == timestamp_key
                ).count()
            
            return 1



class PasswordResetToken(db.Model):
    """Token per reset password"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(100), nullable=False, unique=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=italian_now)
    
    # Relationships
    user = db.relationship('User', backref='password_reset_tokens')
    
    @property
    def is_expired(self):
        """Controlla se il token è scaduto"""
        from datetime import datetime
        # Confronta entrambi in UTC per evitare problemi timezone
        now_utc = datetime.utcnow()
        return now_utc > self.expires_at


class PlatformNews(db.Model):
    """Novità e aggiornamenti della piattaforma gestiti dal SUPERADMIN"""
    __tablename__ = 'platform_news'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    icon_class = db.Column(db.String(100), default='fas fa-info-circle')  # Font Awesome icon class
    icon_color = db.Column(db.String(50), default='text-primary')  # Bootstrap text color class
    active = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, default=0)  # Per ordinare le novità
    created_at = db.Column(db.DateTime, default=italian_now)
    updated_at = db.Column(db.DateTime, default=italian_now, onupdate=italian_now)
    
    def __repr__(self):
        return f'<PlatformNews {self.title}>'
    
    @classmethod
    def get_active_news(cls, limit=None):
        """Recupera le novità attive ordinate"""
        query = cls.query.filter_by(active=True).order_by(cls.order, cls.created_at.desc())
        if limit:
            query = query.limit(limit)
        return query.all()


# =============================================================================
# EXPENSE MANAGEMENT MODELS
# =============================================================================

class ExpenseCategory(db.Model):
    """Categorie per le note spese"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=italian_now)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)  # Multi-tenant
    
    creator = db.relationship('User', backref='created_expense_categories')
    
    def __repr__(self):
        return f'<ExpenseCategory {self.name}>'


class ExpenseReport(db.Model):
    """Note spese dei dipendenti"""
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    expense_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('expense_category.id'), nullable=False)
    receipt_filename = db.Column(db.String(255))  # Nome file allegato
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, approved, rejected
    
    # Approvazione
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    approval_comment = db.Column(db.Text)
    
    # Metadati
    created_at = db.Column(db.DateTime, default=italian_now)
    updated_at = db.Column(db.DateTime, default=italian_now, onupdate=italian_now)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)  # Multi-tenant
    
    # Relationships
    employee = db.relationship('User', foreign_keys=[employee_id], backref='expense_reports')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_expense_reports')
    category = db.relationship('ExpenseCategory', backref='expense_reports')
    
    def __repr__(self):
        return f'<ExpenseReport {self.description[:30]}... - €{self.amount}>'
    
    @property
    def status_display(self):
        """Mostra lo stato in italiano"""
        status_map = {
            'pending': 'In Attesa',
            'approved': 'Approvata',
            'rejected': 'Rifiutata'
        }
        return status_map.get(self.status, self.status)
    
    @property
    def status_color(self):
        """Restituisce il colore Bootstrap per lo stato"""
        color_map = {
            'pending': 'warning',
            'approved': 'success',
            'rejected': 'danger'
        }
        return color_map.get(self.status, 'secondary')
    
    def can_be_edited(self):
        """Verifica se la nota spese può essere modificata"""
        return self.status == 'pending'
    
    def can_be_approved_by(self, user):
        """Verifica se l'utente può approvare questa nota spese"""
        if not user.can_approve_expense_reports():
            return False
            
        # Controllo sede: stesso sede o accesso globale
        if user.all_sedi:
            return True
        
        return user.sede_id == self.employee.sede_id
    
    def approve(self, approver, comment=None):
        """Approva la nota spese"""
        self.status = 'approved'
        self.approved_by = approver.id
        self.approved_at = italian_now()
        self.approval_comment = comment
        
        # Invia notifica automatica al dipendente
        self._send_status_notification()
    
    def reject(self, approver, comment=None):
        """Rifiuta la nota spese"""
        self.status = 'rejected'
        self.approved_by = approver.id
        self.approved_at = italian_now()
        self.approval_comment = comment
        
        # Invia notifica automatica al dipendente
        self._send_status_notification()
    
    def _send_status_notification(self):
        """Invia notifica automatica di cambio stato al dipendente"""
        if self.status == 'approved':
            title = "Nota Spese Approvata"
            message = f"La tua nota spese del {self.expense_date.strftime('%d/%m/%Y')} per €{self.amount} è stata approvata."
            message_type = 'success'
        else:
            title = "Nota Spese Rifiutata"
            message = f"La tua nota spese del {self.expense_date.strftime('%d/%m/%Y')} per €{self.amount} è stata rifiutata."
            message_type = 'danger'
        
        if self.approval_comment:
            message += f"\n\nCommento: {self.approval_comment}"
        
        # Crea messaggio interno
        notification = InternalMessage()
        notification.recipient_id = self.employee_id
        notification.sender_id = self.approved_by
        notification.title = title
        notification.message = message
        notification.message_type = message_type
        
        db.session.add(notification)
    
    @classmethod
    def get_monthly_total(cls, employee_id, year, month, status='approved'):
        """Calcola il totale mensile delle note spese per un dipendente"""
        from sqlalchemy import extract, func
        
        result = db.session.query(func.sum(cls.amount)).filter(
            cls.employee_id == employee_id,
            cls.status == str(status),
            extract('year', cls.expense_date) == year,
            extract('month', cls.expense_date) == month
        ).scalar()
        
        return result or 0
    
    @classmethod
    def get_yearly_total(cls, employee_id, year, status='approved'):
        """Calcola il totale annuale delle note spese per un dipendente"""
        from sqlalchemy import extract, func
        
        result = db.session.query(func.sum(cls.amount)).filter(
            cls.employee_id == employee_id,
            cls.status == str(status),
            extract('year', cls.expense_date) == year
        ).scalar()
        
        return result or 0
    

# =============================================================================
# OVERTIME MANAGEMENT MODELS
# =============================================================================

class OvertimeType(db.Model):
    """Tipologie di straordinario"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    hourly_rate_multiplier = db.Column(db.Float, default=1.5)  # Moltiplicatore per la paga oraria
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=italian_now)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)  # Multi-tenant
    
    def __repr__(self):
        return f'<OvertimeType {self.name}>'


class OvertimeRequest(db.Model):
    """Richieste di straordinario dei dipendenti"""
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    overtime_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    motivation = db.Column(db.Text, nullable=False)
    overtime_type_id = db.Column(db.Integer, db.ForeignKey('overtime_type.id'), nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, approved, rejected
    
    # Approvazione
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    approval_comment = db.Column(db.Text)
    
    # Metadati
    created_at = db.Column(db.DateTime, default=italian_now)
    updated_at = db.Column(db.DateTime, default=italian_now, onupdate=italian_now)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)  # Multi-tenant
    
    # Relationships
    employee = db.relationship('User', foreign_keys=[employee_id], backref='overtime_requests')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_overtime_requests')
    overtime_type = db.relationship('OvertimeType', backref='overtime_requests')
    
    def __repr__(self):
        return f'<OvertimeRequest {self.employee.get_full_name()} - {self.overtime_date}>'
    
    @property
    def status_display(self):
        """Mostra lo stato in italiano"""
        status_map = {
            'pending': 'In Attesa',
            'approved': 'Approvata',
            'rejected': 'Rifiutata'
        }
        return status_map.get(self.status, self.status)
    
    @property
    def status_color(self):
        """Restituisce il colore Bootstrap per lo stato"""
        color_map = {
            'pending': 'warning',
            'approved': 'success',
            'rejected': 'danger'
        }
        return color_map.get(self.status, 'secondary')
    
    @property
    def duration_hours(self):
        """Calcola la durata in ore dello straordinario"""
        from datetime import datetime, timedelta
        
        start_datetime = datetime.combine(self.overtime_date, self.start_time)
        end_datetime = datetime.combine(self.overtime_date, self.end_time)
        
        # Gestisce il caso in cui il turno attraversa la mezzanotte
        if end_datetime <= start_datetime:
            end_datetime += timedelta(days=1)
        
        duration = end_datetime - start_datetime
        return round(duration.total_seconds() / 3600, 2)
    
    @property
    def hours(self):
        """Alias per duration_hours per compatibilità template"""
        return self.duration_hours
    
    def can_be_edited(self):
        """Verifica se la richiesta può essere modificata"""
        return self.status == 'pending'
    
    def can_be_approved_by(self, user):
        """Verifica se l'utente può approvare questa richiesta di straordinario"""
        if not user.can_approve_overtime_requests():
            return False
            
        # Controllo sede: stesso sede o accesso globale
        if user.all_sedi:
            return True
        
        return user.sede_id == self.employee.sede_id
    
    def approve(self, approver, comment=None):
        """Approva la richiesta di straordinario"""
        self.status = 'approved'
        self.approved_by = approver.id
        self.approved_at = italian_now()
        self.approval_comment = comment
        
        # Invia notifica automatica al dipendente
        self._send_status_notification()
    
    def reject(self, approver, comment=None):
        """Rifiuta la richiesta di straordinario"""
        self.status = 'rejected'
        self.approved_by = approver.id
        self.approved_at = italian_now()
        self.approval_comment = comment
        
        # Invia notifica automatica al dipendente
        self._send_status_notification()
    
    def _send_status_notification(self):
        """Invia notifica automatica del cambio di stato al dipendente"""
        try:
            if self.status == 'approved':
                title = "Straordinario Approvato"
                message = f"La tua richiesta di straordinario per il {self.overtime_date.strftime('%d/%m/%Y')} dalle {self.start_time.strftime('%H:%M')} alle {self.end_time.strftime('%H:%M')} è stata approvata."
                message_type = 'Successo'
            else:
                title = "Straordinario Rifiutato"
                message = f"La tua richiesta di straordinario per il {self.overtime_date.strftime('%d/%m/%Y')} dalle {self.start_time.strftime('%H:%M')} alle {self.end_time.strftime('%H:%M')} è stata rifiutata."
                message_type = 'Attenzione'
            
            if self.approval_comment:
                message += f"\n\nCommento: {self.approval_comment}"
            
            # Crea messaggio interno
            notification = InternalMessage()
            notification.recipient_id = self.employee_id
            notification.sender_id = self.approved_by
            notification.title = title
            notification.message = message
            notification.message_type = message_type
            
            db.session.add(notification)
                
        except Exception as e:
            # Notification error handled by messaging system
            pass

    @classmethod
    def get_monthly_hours(cls, employee_id, year, month, status='approved'):
        """Calcola il totale mensile delle ore di straordinario per un dipendente"""
        from sqlalchemy import extract, func
        
        requests = db.session.query(cls).filter(
            cls.employee_id == employee_id,
            cls.status == str(status),
            extract('year', cls.overtime_date) == year,
            extract('month', cls.overtime_date) == month
        ).all()
        
        total_hours = sum(request.duration_hours for request in requests)
        return round(total_hours, 2)


# =============================================================================
# MILEAGE MANAGEMENT MODELS
# =============================================================================

class MileageRequest(db.Model):
    """Richieste di rimborso chilometrico dei dipendenti"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    travel_date = db.Column(db.Date, nullable=False)
    
    # Percorso multi-punto (JSON array di indirizzi)
    route_addresses = db.Column(db.JSON, nullable=False)  # ["Via Roma 32, Milano", "Via Milano 2, Roma", ...]
    
    # Chilometraggio
    total_km = db.Column(db.Float, nullable=False)
    calculated_km = db.Column(db.Float, nullable=True)  # KM calcolati automaticamente
    is_km_manual = db.Column(db.Boolean, default=False)  # Se i KM sono stati inseriti manualmente
    
    # Veicolo utilizzato
    vehicle_id = db.Column(db.Integer, db.ForeignKey('aci_table.id'), nullable=True)
    vehicle_description = db.Column(db.String(200))  # Descrizione del veicolo se non in ACI
    
    # Calcolo rimborso
    cost_per_km = db.Column(db.Float, nullable=False)  # Costo per km al momento della richiesta
    total_amount = db.Column(db.Float, nullable=False)  # Importo totale calcolato
    
    # Motivazione e note
    purpose = db.Column(db.Text, nullable=False)  # Scopo del viaggio
    notes = db.Column(db.Text)  # Note aggiuntive
    
    # Status e approvazione
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, approved, rejected
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    approval_comment = db.Column(db.Text)
    
    # Metadati
    created_at = db.Column(db.DateTime, default=italian_now)
    updated_at = db.Column(db.DateTime, default=italian_now, onupdate=italian_now)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)  # Multi-tenant
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='mileage_requests')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_mileage_requests')
    vehicle = db.relationship('ACITable', backref='mileage_requests')
    
    def __repr__(self):
        return f'<MileageRequest {self.user.get_full_name()} - {self.travel_date} - {self.total_km}km>'
    
    @property
    def status_display(self):
        """Mostra lo stato in italiano"""
        status_map = {
            'pending': 'In Attesa',
            'approved': 'Approvata',
            'rejected': 'Rifiutata'
        }
        return status_map.get(self.status, self.status)
    
    @property
    def status_color(self):
        """Restituisce il colore Bootstrap per lo stato"""
        color_map = {
            'pending': 'warning',
            'approved': 'success',
            'rejected': 'danger'
        }
        return color_map.get(self.status, 'secondary')
    
    @property
    def route_display(self):
        """Restituisce il percorso in formato leggibile"""
        if not self.route_addresses:
            return "Percorso non specificato"
        
        if len(self.route_addresses) <= 2:
            return " → ".join(self.route_addresses)
        else:
            # Per percorsi multi-punto, mostra partenza → ... → destinazione
            return f"{self.route_addresses[0]} → ... → {self.route_addresses[-1]} ({len(self.route_addresses)} punti)"
    
    @property
    def route_full_display(self):
        """Restituisce il percorso completo"""
        if not self.route_addresses:
            return "Percorso non specificato"
        return " → ".join(self.route_addresses)
    
    def get_route_list(self):
        """Restituisce la lista degli indirizzi del percorso"""
        if not self.route_addresses:
            return []
        return self.route_addresses
    
    def can_be_edited(self):
        """Verifica se la richiesta può essere modificata"""
        return self.status == 'pending'
    
    def can_be_approved_by(self, user):
        """Verifica se l'utente può approvare questa richiesta di rimborso"""
        if not user.can_approve_mileage_requests():
            return False
            
        # Controllo sede: stesso sede o accesso globale
        if user.all_sedi:
            return True
        
        return user.sede_id == self.user.sede_id
    
    def approve(self, approver, comment=None):
        """Approva la richiesta di rimborso chilometrico"""
        self.status = 'approved'
        self.approved_by = approver.id
        self.approved_at = italian_now()
        self.approval_comment = comment
        
        # Invia notifica di approvazione
        notification = InternalMessage()
        notification.recipient_id = self.user_id
        notification.sender_id = approver.id
        notification.title = "Rimborso Chilometrico Approvato"
        notification.message = f"Il tuo rimborso chilometrico per {self.total_km}km del {self.travel_date.strftime('%d/%m/%Y')} è stato approvato per un importo di €{self.total_amount:.2f}. {comment or ''}"
        notification.message_type = 'Successo'
        db.session.add(notification)
    
    def reject(self, approver, comment=None):
        """Rifiuta la richiesta di rimborso chilometrico"""
        self.status = 'rejected'
        self.approved_by = approver.id
        self.approved_at = italian_now()
        self.approval_comment = comment
        
        # Invia notifica di rifiuto
        notification = InternalMessage()
        notification.recipient_id = self.user_id
        notification.sender_id = approver.id
        notification.title = "Rimborso Chilometrico Rifiutato"
        notification.message = f"Il tuo rimborso chilometrico per {self.total_km}km del {self.travel_date.strftime('%d/%m/%Y')} è stato rifiutato. Motivo: {comment or 'Nessun motivo specificato'}"
        notification.message_type = 'Attenzione'
        db.session.add(notification)
    
    def calculate_reimbursement_amount(self):
        """Calcola l'importo del rimborso basato sui km e sul veicolo"""
        from decimal import Decimal
        
        if self.vehicle_id:
            # Usa il costo ACI del veicolo assegnato
            vehicle = ACITable.query.get(self.vehicle_id)
            if vehicle:
                # Converti Decimal in float per compatibilità
                self.cost_per_km = float(vehicle.costo_km)
            else:
                # Fallback - costo medio se il veicolo non esiste
                self.cost_per_km = 0.3500  # €0.35/km come media
        else:
            # Usa costo standard per veicoli non ACI
            self.cost_per_km = 0.3500  # €0.35/km come standard
        
        # Calcola l'importo totale
        self.total_amount = round(float(self.total_km) * float(self.cost_per_km), 2)
    
    @classmethod
    def get_pending_count_for_user(cls, user):
        """Restituisce il numero di richieste in attesa per l'utente"""
        query = cls.query.filter_by(status='pending')
        
        if user.all_sedi:
            return query.count()
        else:
            return query.join(User, cls.user_id == User.id).filter(
                User.sede_id == user.sede_id
            ).count()
    
    @classmethod
    def get_monthly_summary(cls, user_id, year, month):
        """Restituisce un riassunto mensile dei rimborsi per un dipendente"""
        from sqlalchemy import extract
        
        query = cls.query.filter(
            cls.user_id == user_id,
            extract('year', cls.travel_date) == year,
            extract('month', cls.travel_date) == month
        )
        
        # Calcola totali per stato
        pending = query.filter_by(status='pending').all()
        approved = query.filter_by(status='approved').all()
        rejected = query.filter_by(status='rejected').all()
        
        return {
            'pending_count': len(pending),
            'approved_count': len(approved),
            'rejected_count': len(rejected),
            'pending_km': sum([req.total_km for req in pending]),
            'approved_km': sum([req.total_km for req in approved]),
            'pending_amount': sum([req.total_amount for req in pending]),
            'approved_amount': sum([req.total_amount for req in approved]),
            'total_km': sum([req.total_km for req in pending + approved + rejected]),
            'total_amount': sum([req.total_amount for req in pending + approved + rejected])
        }


# =============================================================================
# SYSTEM CONFIGURATION MODELS
# =============================================================================

class Company(db.Model):
    """Modello per le aziende - Multi-tenant system"""
    __tablename__ = 'company'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)  # ES: NS12, ATMH
    slug = db.Column(db.String(50), unique=True, nullable=False)  # URL-friendly slug per path-based tenant (es: ns12, azienda1)
    description = db.Column(db.Text, nullable=True)
    logo = db.Column(db.String(500), nullable=True)  # Path al file logo
    background_image = db.Column(db.String(500), nullable=True)  # Path all'immagine di sfondo
    max_licenses = db.Column(db.Integer, default=10, nullable=False)  # Numero massimo di licenze/utenti attivi
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=italian_now)
    
    # Relazioni
    users = db.relationship('User', back_populates='company', lazy='dynamic')
    sedi = db.relationship('Sede', back_populates='company', lazy='dynamic')
    
    def __repr__(self):
        return f'<Company {self.code} - {self.name}>'


class CompanyEmailSettings(db.Model):
    """Configurazione SMTP specifica per ogni azienda - Multi-tenant email system"""
    __tablename__ = 'company_email_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False, unique=True)
    
    # Configurazione SMTP
    mail_server = db.Column(db.String(255), nullable=False)  # es: smtp.gmail.com
    mail_port = db.Column(db.Integer, default=587, nullable=False)
    mail_use_tls = db.Column(db.Boolean, default=True, nullable=False)
    mail_use_ssl = db.Column(db.Boolean, default=False, nullable=False)
    mail_username = db.Column(db.String(255), nullable=False)
    mail_password_encrypted = db.Column(db.Text, nullable=False)  # Password criptata con Fernet
    mail_default_sender = db.Column(db.String(255), nullable=False)  # Email mittente
    mail_reply_to = db.Column(db.String(255), nullable=True)  # Email reply-to (opzionale)
    
    # Stato e diagnostica
    active = db.Column(db.Boolean, default=True, nullable=False)
    last_tested_at = db.Column(db.DateTime, nullable=True)
    test_status = db.Column(db.String(20), nullable=True)  # 'success', 'failed'
    test_error = db.Column(db.Text, nullable=True)  # Ultimo errore di test
    
    created_at = db.Column(db.DateTime, default=italian_now)
    updated_at = db.Column(db.DateTime, default=italian_now, onupdate=italian_now)
    
    # Relazione
    company = db.relationship('Company', backref=db.backref('email_settings', uselist=False, lazy=True))
    
    def __repr__(self):
        return f'<CompanyEmailSettings for {self.company.name if self.company else "Unknown"}>'
    
    def get_decrypted_password(self):
        """Decripta e restituisce la password SMTP"""
        from utils_encryption import decrypt_value
        return decrypt_value(self.mail_password_encrypted)
    
    def set_password(self, plain_password):
        """Cripta e salva la password SMTP"""
        from utils_encryption import encrypt_value
        self.mail_password_encrypted = encrypt_value(plain_password)


class Sede(db.Model):
    """Modello per le sedi aziendali"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    address = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)
    tipologia = db.Column(db.String(20), nullable=False, default='Oraria')  # 'Oraria' o 'Turni'
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=italian_now)
    
    # Multi-tenant field
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)
    
    # Relationships (users già definito tramite backref in User)
    company = db.relationship('Company', back_populates='sedi')
    
    def __repr__(self):
        return f'<Sede {self.name}>'
    
    def is_turni_mode(self):
        """Restituisce True se la sede opera con modalità turni"""
        return self.tipologia == 'Turni'
    
    def is_oraria_mode(self):
        """Restituisce True se la sede opera con modalità oraria"""
        return self.tipologia == 'Oraria'


class WorkSchedule(db.Model):
    """Modello per gli orari di lavoro aziendali globali (a livello company)"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    
    # Range orario di inizio (entrata)
    start_time_min = db.Column(db.Time, nullable=False)  # Orario minimo di entrata
    start_time_max = db.Column(db.Time, nullable=False)  # Orario massimo di entrata
    
    # Range orario di fine (uscita)
    end_time_min = db.Column(db.Time, nullable=False)    # Orario minimo di uscita
    end_time_max = db.Column(db.Time, nullable=False)    # Orario massimo di uscita
    
    # Campi legacy per compatibilità (deprecati)
    start_time = db.Column(db.Time, nullable=True)  # Mantenuto per compatibilità
    end_time = db.Column(db.Time, nullable=True)    # Mantenuto per compatibilità
    
    days_of_week = db.Column(db.JSON, nullable=False, default=list)  # Lista dei giorni della settimana [0,1,2,3,4] per Lun-Ven
    description = db.Column(db.Text, nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=italian_now)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)  # Multi-tenant
    
    # Constraint per evitare duplicati nella stessa azienda
    __table_args__ = (db.UniqueConstraint('company_id', 'name', name='_company_schedule_name_uc'),)
    
    def __repr__(self):
        return f'<WorkSchedule {self.name}>'
    
    def get_days_of_week_list(self):
        """Restituisce la lista dei giorni della settimana come interi"""
        if not self.days_of_week:
            return []
        # Assicurati che sia una lista e non una stringa JSON
        if isinstance(self.days_of_week, str):
            import json
            try:
                return json.loads(self.days_of_week)
            except:
                return []
        return self.days_of_week if isinstance(self.days_of_week, list) else []
    
    def get_duration_hours(self):
        """Calcola la durata media in ore dell'orario di lavoro basandosi sui range"""
        # Usa il punto medio dei range per calcolare la durata media
        avg_start_minutes = ((self.start_time_min.hour * 60 + self.start_time_min.minute) + 
                            (self.start_time_max.hour * 60 + self.start_time_max.minute)) / 2
        avg_end_minutes = ((self.end_time_min.hour * 60 + self.end_time_min.minute) + 
                          (self.end_time_max.hour * 60 + self.end_time_max.minute)) / 2
        
        # Gestisci il caso di orario che attraversa la mezzanotte
        if avg_end_minutes < avg_start_minutes:
            avg_end_minutes += 24 * 60
        
        duration_minutes = avg_end_minutes - avg_start_minutes
        return duration_minutes / 60.0
    
    def get_start_range_display(self):
        """Restituisce il range di orario di inizio formattato"""
        if self.start_time_min == self.start_time_max:
            return self.start_time_min.strftime('%H:%M')
        return f"{self.start_time_min.strftime('%H:%M')} - {self.start_time_max.strftime('%H:%M')}"
    
    def get_end_range_display(self):
        """Restituisce il range di orario di fine formattato"""
        if self.end_time_min == self.end_time_max:
            return self.end_time_min.strftime('%H:%M')
        return f"{self.end_time_min.strftime('%H:%M')} - {self.end_time_max.strftime('%H:%M')}"
    
    def is_turni_schedule(self):
        """Verifica se questo è un orario di tipo 'Turni'"""
        return self.name == 'Turni'
    
    @property
    def duration_display(self):
        """Formato di visualizzazione della durata"""
        hours = self.get_duration_hours()
        return f"{hours:.1f}h"
    
    def get_days_display(self):
        """Restituisce i giorni della settimana in formato leggibile"""
        days_names = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
        if not self.days_of_week:
            return 'Nessun giorno'
        
        selected_days = [days_names[day] for day in self.days_of_week if day is not None and 0 <= day < 7]
        
        # Controlla pattern comuni
        if self.days_of_week == [0, 1, 2, 3, 4]:
            return 'Lunedì-Venerdì'
        elif self.days_of_week == [5, 6]:
            return 'Sabato-Domenica'
        elif len(selected_days) == 7:
            return 'Tutti i giorni'
        elif len(selected_days) <= 3:
            return ', '.join(selected_days)
        else:
            return f"{', '.join(selected_days[:-1])} e {selected_days[-1]}"
    
    def set_days_from_list(self, days_list):
        """Imposta i giorni della settimana da una lista di stringhe"""
        day_mapping = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        self.days_of_week = [day_mapping.get(day.lower()) for day in days_list if day.lower() in day_mapping]
        self.days_of_week = [day for day in self.days_of_week if day is not None]
    
    @staticmethod
    def get_weekday_presets():
        """Restituisce i preset comuni per i giorni della settimana"""
        return {
            'workdays': ([0, 1, 2, 3, 4], 'Lunedì-Venerdì'),
            'weekend': ([5, 6], 'Sabato-Domenica'),
            'all_week': ([0, 1, 2, 3, 4, 5, 6], 'Tutti i giorni'),
            'custom': ([], 'Personalizzato')
        }


class ACITable(db.Model):
    """Modello per le tabelle ACI (Automobile Club d'Italia) - Back office amministratore"""
    __tablename__ = 'aci_table'
    
    id = db.Column(db.Integer, primary_key=True)
    tipologia = db.Column(db.String(100), nullable=False)  # Nome file Excel caricato
    marca = db.Column(db.String(100), nullable=False)
    modello = db.Column(db.String(200), nullable=False)
    costo_km = db.Column(db.Numeric(10, 4), nullable=False)  # Costo per KM
    created_at = db.Column(db.DateTime, default=italian_now)
    updated_at = db.Column(db.DateTime, default=italian_now, onupdate=italian_now)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)  # Multi-tenant
    
    def __repr__(self):
        return f'<ACITable {self.marca} {self.modello}>'
    
    def to_dict(self):
        """Converte il record in dizionario per JSON"""
        return {
            'id': self.id,
            'tipologia': self.tipologia,
            'marca': self.marca,
            'modello': self.modello,
            'costo_km': float(self.costo_km) if self.costo_km else None,
            'created_at': self.created_at.strftime('%d/%m/%Y %H:%M') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%d/%m/%Y %H:%M') if self.updated_at else None
        }


# =============================================================================
# CIRCLE MODELS - Social Intranet Aziendale
# =============================================================================

class CirclePost(db.Model):
    """Modello per post/news CIRCLE (Delorean, News, Feed)"""
    __tablename__ = 'circle_post'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    post_type = db.Column(db.String(50), nullable=False)  # 'news', 'delorean', 'announcement', 'tech_feed'
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    published = db.Column(db.Boolean, default=True)
    pinned = db.Column(db.Boolean, default=False)  # Post in evidenza
    comments_enabled = db.Column(db.Boolean, default=True)  # Abilitazione commenti
    image_url = db.Column(db.String(255), nullable=True)  # Immagine allegata
    video_url = db.Column(db.String(255), nullable=True)  # Video allegato
    created_at = db.Column(db.DateTime, default=italian_now)
    updated_at = db.Column(db.DateTime, default=italian_now, onupdate=italian_now)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)  # Multi-tenant
    
    # Relationships
    author = db.relationship('User', backref='circle_posts')
    
    def __repr__(self):
        return f'<CirclePost {self.title}>'
    
    def get_like_count(self):
        """Restituisce il numero di like"""
        return len(self.likes)
    
    def get_comment_count(self):
        """Restituisce il numero di commenti"""
        return len(self.comments) if self.comments_enabled else 0
    
    def is_liked_by(self, user):
        """Verifica se l'utente ha già messo like"""
        return any(like.user_id == user.id for like in self.likes)


class CircleGroup(db.Model):
    """Modello per gruppi sociali aziendali CIRCLE"""
    __tablename__ = 'circle_group'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    group_type = db.Column(db.String(50), nullable=False)  # 'department', 'project', 'interest', 'official'
    is_private = db.Column(db.Boolean, default=False)  # Gruppo privato (solo su invito)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    image_url = db.Column(db.String(255), nullable=True)  # Immagine del gruppo
    created_at = db.Column(db.DateTime, default=italian_now)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)  # Multi-tenant
    
    # Relationships
    creator = db.relationship('User', backref='created_groups')
    members = db.relationship('User', secondary='circle_group_members', backref='joined_groups')
    
    def __repr__(self):
        return f'<CircleGroup {self.name}>'
    
    def is_member(self, user):
        """Verifica se l'utente è membro del gruppo"""
        return user in self.members or user.id == self.creator_id
    
    def is_admin(self, user):
        """Verifica se l'utente è admin del gruppo"""
        if user.id == self.creator_id:
            return True
        result = db.session.execute(
            db.select(circle_group_members).where(
                circle_group_members.c.user_id == user.id,
                circle_group_members.c.group_id == self.id,
                circle_group_members.c.is_admin == True
            )
        ).first()
        return result is not None
    
    def get_member_count(self):
        """Restituisce il numero di membri"""
        return len(self.members) + 1  # +1 per il creatore
    
    def has_pending_request(self, user):
        """Verifica se l'utente ha una richiesta pendente"""
        from models import CircleGroupMembershipRequest
        return CircleGroupMembershipRequest.query.filter_by(
            group_id=self.id,
            user_id=user.id,
            status='pending'
        ).first() is not None
    
    def can_access(self, user):
        """Verifica se l'utente può accedere al gruppo"""
        if not self.is_private:
            return True
        return self.is_member(user)


# Tabella associativa many-to-many per membri dei gruppi
circle_group_members = db.Table('circle_group_members',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('group_id', db.Integer, db.ForeignKey('circle_group.id'), primary_key=True),
    db.Column('is_admin', db.Boolean, default=False),  # Admin del gruppo
    db.Column('joined_at', db.DateTime, default=italian_now)
)


class CirclePoll(db.Model):
    """Modello per sondaggi CIRCLE"""
    __tablename__ = 'circle_poll'
    
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_anonymous = db.Column(db.Boolean, default=False)  # Voti anonimi
    multiple_choice = db.Column(db.Boolean, default=False)  # Scelta multipla
    end_date = db.Column(db.DateTime, nullable=True)  # Data chiusura sondaggio
    created_at = db.Column(db.DateTime, default=italian_now)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)  # Multi-tenant
    
    # Relationships
    creator = db.relationship('User', backref='created_polls')
    
    def has_voted(self, user):
        """Verifica se l'utente ha già votato"""
        return CirclePollVote.query.filter_by(poll_id=self.id, user_id=user.id).first() is not None
    
    def is_closed(self):
        """Verifica se il sondaggio è chiuso"""
        if self.end_date is None:
            return False
        from datetime import datetime
        return italian_now() > self.end_date
    
    def get_vote_count(self):
        """Conta totale dei voti"""
        return len(self.votes)
    
    def get_results(self):
        """Ottiene i risultati del sondaggio con percentuali"""
        total_votes = self.get_vote_count()
        results = []
        
        for option in self.options:
            vote_count = len(option.votes)
            percentage = (vote_count / total_votes * 100) if total_votes > 0 else 0
            results.append({
                'option': option,
                'votes': vote_count,
                'percentage': round(percentage, 1)
            })
        
        return results
    
    def get_user_votes(self, user):
        """Ottiene le opzioni votate dall'utente"""
        votes = CirclePollVote.query.filter_by(poll_id=self.id, user_id=user.id).all()
        return [vote.option_id for vote in votes]
    
    def __repr__(self):
        return f'<CirclePoll {self.question}>'


class CirclePollOption(db.Model):
    """Opzioni per i sondaggi CIRCLE"""
    __tablename__ = 'circle_poll_option'
    
    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey('circle_poll.id'), nullable=False)
    option_text = db.Column(db.String(200), nullable=False)
    
    # Relationships
    poll = db.relationship('CirclePoll', backref='options')
    
    def __repr__(self):
        return f'<CirclePollOption {self.option_text}>'


class CirclePollVote(db.Model):
    """Voti ai sondaggi CIRCLE"""
    __tablename__ = 'circle_poll_vote'
    
    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey('circle_poll.id'), nullable=False)
    option_id = db.Column(db.Integer, db.ForeignKey('circle_poll_option.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    voted_at = db.Column(db.DateTime, default=italian_now)
    
    # Relationships
    poll = db.relationship('CirclePoll', backref='votes')
    option = db.relationship('CirclePollOption', backref='votes')
    user = db.relationship('User', backref='poll_votes')
    
    def __repr__(self):
        return f'<CirclePollVote Poll#{self.poll_id} Option#{self.option_id}>'


class CircleDocument(db.Model):
    """Modello per documenti Qualità/HR CIRCLE"""
    __tablename__ = 'circle_document'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False)  # 'quality', 'hr', 'procedure', 'form'
    file_path = db.Column(db.String(255), nullable=False)  # Path del file
    file_type = db.Column(db.String(50), nullable=True)  # pdf, docx, xlsx, etc
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    version = db.Column(db.String(20), default='1.0')  # Versione documento
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=italian_now)
    updated_at = db.Column(db.DateTime, default=italian_now, onupdate=italian_now)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)  # Multi-tenant
    
    # Relationships
    uploader = db.relationship('User', backref='uploaded_documents')
    
    def __repr__(self):
        return f'<CircleDocument {self.title}>'


class CircleCalendarEvent(db.Model):
    """Modello per eventi calendario aziendale CIRCLE"""
    __tablename__ = 'circle_calendar_event'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    event_type = db.Column(db.String(50), nullable=False)  # 'meeting', 'deadline', 'holiday', 'event'
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200), nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_all_day = db.Column(db.Boolean, default=False)
    color = db.Column(db.String(20), default='#0d6efd')  # Colore evento
    created_at = db.Column(db.DateTime, default=italian_now)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)  # Multi-tenant
    
    # Relationships
    creator = db.relationship('User', backref='created_events')
    
    def __repr__(self):
        return f'<CircleCalendarEvent {self.title}>'


class CircleComment(db.Model):
    """Modello per commenti ai post CIRCLE"""
    __tablename__ = 'circle_comment'
    
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('circle_post.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=italian_now)
    updated_at = db.Column(db.DateTime, default=italian_now, onupdate=italian_now)
    
    # Relationships
    post = db.relationship('CirclePost', backref='comments')
    author = db.relationship('User', backref='comments')
    
    def __repr__(self):
        return f'<CircleComment Post#{self.post_id}>'


class CircleLike(db.Model):
    """Modello per like ai post CIRCLE"""
    __tablename__ = 'circle_like'
    
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('circle_post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=italian_now)
    
    # Relationships
    post = db.relationship('CirclePost', backref='likes')
    user = db.relationship('User', backref='liked_posts')
    
    def __repr__(self):
        return f'<CircleLike Post#{self.post_id} User#{self.user_id}>'


class CircleToolLink(db.Model):
    """Modello per scorciatoie strumenti esterni CIRCLE"""
    __tablename__ = 'circle_tool_link'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    url = db.Column(db.String(255), nullable=False)
    icon = db.Column(db.String(50), nullable=True)  # Font Awesome icon class
    category = db.Column(db.String(50), nullable=False)  # 'productivity', 'communication', 'hr', 'custom'
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)  # Multi-tenant
    
    def __repr__(self):
        return f'<CircleToolLink {self.name}>'


class CircleGroupMembershipRequest(db.Model):
    """Modello per richieste di adesione ai gruppi CIRCLE"""
    __tablename__ = 'circle_group_membership_request'
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('circle_group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'accepted', 'rejected'
    message = db.Column(db.Text, nullable=True)  # Messaggio di richiesta
    created_at = db.Column(db.DateTime, default=italian_now)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Relationships
    group = db.relationship('CircleGroup', backref='membership_requests')
    user = db.relationship('User', foreign_keys=[user_id], backref='group_requests')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by], backref='reviewed_requests')
    
    def __repr__(self):
        return f'<CircleGroupMembershipRequest Group#{self.group_id} User#{self.user_id}>'


class CircleGroupPost(db.Model):
    """Modello per post nella bacheca dei gruppi CIRCLE"""
    __tablename__ = 'circle_group_post'
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('circle_group.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    file_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=italian_now)
    updated_at = db.Column(db.DateTime, default=italian_now, onupdate=italian_now)
    
    # Relationships
    group = db.relationship('CircleGroup', backref='posts')
    author = db.relationship('User', backref='group_posts')
    
    def get_like_count(self):
        """Ritorna il numero di like del post"""
        return len(self.likes)
    
    def is_liked_by(self, user):
        """Verifica se l'utente ha messo like al post"""
        return any(like.user_id == user.id for like in self.likes)
    
    def get_comment_count(self):
        """Ritorna il numero di commenti del post"""
        return len(self.comments)
    
    def __repr__(self):
        return f'<CircleGroupPost Group#{self.group_id}>'


class CircleGroupPostLike(db.Model):
    """Modello per like ai post dei gruppi CIRCLE"""
    __tablename__ = 'circle_group_post_like'
    
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('circle_group_post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=italian_now)
    
    # Relationships
    post = db.relationship('CircleGroupPost', backref='likes')
    user = db.relationship('User', backref='group_post_likes')
    
    def __repr__(self):
        return f'<CircleGroupPostLike Post#{self.post_id} User#{self.user_id}>'


class CircleGroupPostComment(db.Model):
    """Modello per commenti ai post dei gruppi CIRCLE"""
    __tablename__ = 'circle_group_post_comment'
    
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('circle_group_post.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=italian_now)
    updated_at = db.Column(db.DateTime, default=italian_now, onupdate=italian_now)
    
    # Relationships
    post = db.relationship('CircleGroupPost', backref='comments')
    author = db.relationship('User', backref='group_post_comments')
    
    def __repr__(self):
        return f'<CircleGroupPostComment Post#{self.post_id} Author#{self.author_id}>'


class CircleGroupMessage(db.Model):
    """Modello per messaggi diretti tra membri dei gruppi CIRCLE"""
    __tablename__ = 'circle_group_message'
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('circle_group.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=italian_now)
    
    # Relationships
    group = db.relationship('CircleGroup', backref='messages')
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_group_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_group_messages')
    
    def __repr__(self):
        return f'<CircleGroupMessage Group#{self.group_id} From#{self.sender_id} To#{self.recipient_id}>'


class ConnectionRequest(db.Model):
    """Modello per richieste di connessione tra utenti CIRCLE (Personas)"""
    __tablename__ = 'connection_request'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # 'pending', 'accepted', 'rejected'
    created_at = db.Column(db.DateTime, default=italian_now)
    responded_at = db.Column(db.DateTime, nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)  # Multi-tenant
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_connection_requests')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_connection_requests')
    
    # Constraint per evitare richieste duplicate
    __table_args__ = (
        db.UniqueConstraint('sender_id', 'recipient_id', name='unique_connection_request'),
    )
    
    def __repr__(self):
        return f'<ConnectionRequest From#{self.sender_id} To#{self.recipient_id} Status:{self.status}>'


# =============================================================================
# PROJECT MANAGEMENT MODELS (COMMESSE)
# =============================================================================

# Tabella di associazione many-to-many tra User e Commessa
commessa_assignment = db.Table('commessa_assignment',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('commessa_id', db.Integer, db.ForeignKey('commessa.id'), primary_key=True),
    db.Column('assigned_at', db.DateTime, default=italian_now),
    db.Column('assigned_by_id', db.Integer, db.ForeignKey('user.id'), nullable=True)
)


class Commessa(db.Model):
    """Modello per la gestione delle commesse aziendali"""
    __tablename__ = 'commessa'
    __table_args__ = (
        db.UniqueConstraint('titolo', 'company_id', name='_titolo_company_uc'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    cliente = db.Column(db.String(200), nullable=False)
    titolo = db.Column(db.String(200), nullable=False)
    descrizione = db.Column(db.Text, nullable=True)
    attivita = db.Column(db.String(100), nullable=False)
    data_inizio = db.Column(db.Date, nullable=False)
    data_fine = db.Column(db.Date, nullable=False)
    durata_prevista_ore = db.Column(db.Integer, nullable=True)
    stato = db.Column(db.String(20), nullable=False, default='attiva')  # 'attiva', 'in corso', 'chiusa'
    tariffa_oraria = db.Column(db.Numeric(10, 2), nullable=True)
    note = db.Column(db.Text, nullable=True)
    
    # Multi-tenant
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=italian_now)
    updated_at = db.Column(db.DateTime, default=italian_now, onupdate=italian_now)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Relationships
    company = db.relationship('Company', backref='commesse')
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_commesse')
    assigned_users = db.relationship('User', 
                                     secondary=commessa_assignment, 
                                     primaryjoin='Commessa.id==commessa_assignment.c.commessa_id',
                                     secondaryjoin='User.id==commessa_assignment.c.user_id',
                                     backref='assigned_commesse')
    
    def __repr__(self):
        return f'<Commessa {self.titolo} - {self.cliente}>'
    
    def get_ore_consumate(self):
        """Calcola le ore consumate sulla commessa (placeholder per futura integrazione con timesheet)"""
        # TODO: implementare calcolo ore dalle presenze/timesheet
        return 0
    
    def get_ore_residue(self):
        """Calcola le ore residue della commessa"""
        if self.durata_prevista_ore:
            return self.durata_prevista_ore - self.get_ore_consumate()
        return None
    
    def get_percentuale_completamento(self):
        """Calcola la percentuale di completamento"""
        if self.durata_prevista_ore and self.durata_prevista_ore > 0:
            ore_consumate = self.get_ore_consumate()
            return min(100, int((ore_consumate / self.durata_prevista_ore) * 100))
        return 0
    
    def is_scaduta(self):
        """Verifica se la commessa è scaduta"""
        return date.today() > self.data_fine and self.stato != 'chiusa'
    
    def get_giorni_rimanenti(self):
        """Calcola i giorni rimanenti alla scadenza"""
        if self.stato == 'chiusa':
            return 0
        delta = self.data_fine - date.today()
        return max(0, delta.days)