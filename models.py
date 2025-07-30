from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from flask_login import UserMixin
from app import db

# Funzione helper per timestamp italiano
def italian_now():
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

class UserRole(db.Model):
    """Modello per la gestione dinamica dei ruoli utente"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    permissions = db.Column(db.JSON, default=dict)  # Permessi in formato JSON
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=italian_now)
    
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
            'can_view_reperibilita': 'Visualizzare Reperibilità',
            'can_manage_coverage': 'Gestire Coperture Reperibilità',
            'can_view_coverage': 'Visualizzare Coperture Reperibilità',
            
            # Gestione presenze
            'can_manage_attendance': 'Gestire Presenze',
            'can_view_attendance': 'Visualizzare Presenze',
            'can_access_attendance': 'Accedere alle Presenze',
            'can_view_sede_attendance': 'Visualizzare Presenze Sede',
            
            # Gestione ferie/permessi
            'can_manage_leave': 'Gestire Ferie/Permessi',
            'can_manage_leave_types': 'Gestire Tipologie Permessi',
            'can_approve_leave': 'Approvare Ferie/Permessi',
            'can_request_leave': 'Richiedere Ferie/Permessi',
            'can_view_leave': 'Visualizzare Ferie/Permessi',
            
            # Gestione interventi
            'can_manage_interventions': 'Gestire Interventi',
            'can_view_interventions': 'Visualizzare Interventi',
            
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
            'can_view_expense_reports': 'Visualizzare Note Spese',
            'can_approve_expense_reports': 'Approvare Note Spese',
            'can_create_expense_reports': 'Creare Note Spese',
            'can_view_my_expense_reports': 'Visualizzare Le Mie Note Spese',
            
            # Straordinari
            'can_create_overtime_requests': 'Creare Richieste Straordinario',
            'can_view_overtime_requests': 'Visualizzare Richieste Straordinario',
            'can_manage_overtime_requests': 'Gestire Richieste Straordinario',
            'can_approve_overtime_requests': 'Approvare Richieste Straordinario',
            'can_create_overtime_types': 'Creare Tipologie Straordinario',
            'can_view_overtime_types': 'Visualizzare Tipologie Straordinario',
            'can_manage_overtime_types': 'Gestire Tipologie Straordinario',
            'can_view_my_overtime_requests': 'Visualizzare Le Mie Richieste Straordinario',
            
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
            'can_view_my_overtime_widget': 'Widget I Miei Straordinari'
        }

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # Ora referenzia UserRole.name
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=True)  # Sede principale (legacy)
    all_sedi = db.Column(db.Boolean, default=False)  # True se l'utente può accedere a tutte le sedi
    work_schedule_id = db.Column(db.Integer, db.ForeignKey('work_schedule.id'), nullable=True)  # Orario di lavoro specifico
    active = db.Column(db.Boolean, default=True)  # Renamed to avoid UserMixin conflict
    part_time_percentage = db.Column(db.Float, default=100.0)  # Percentuale di lavoro: 100% = tempo pieno, 50% = metà tempo, ecc.
    created_at = db.Column(db.DateTime, default=italian_now)
    
    # Relationship con Sede e WorkSchedule
    sede_obj = db.relationship('Sede', backref='users')
    work_schedule = db.relationship('WorkSchedule', backref='assigned_users')
    
    # La relazione con AttendanceEvent è già definita tramite backref in AttendanceEvent.user
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_accessible_sedi(self):
        """Restituisce tutte le sedi accessibili dall'utente"""
        if self.all_sedi:
            return Sede.query.filter_by(active=True).all()
        elif self.sede_id:
            return [self.sede_obj] if self.sede_obj and self.sede_obj.active else []
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
        return UserRole.query.filter_by(name=self.role).first()
    
    def has_permission(self, permission):
        """Verifica se l'utente ha un determinato permesso tramite il suo ruolo"""
        role_obj = self.get_role_obj()
        if role_obj:
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
    
    def can_view_shifts(self):
        return self.has_permission('can_view_shifts')
    
    # === REPERIBILITÀ ===
    def can_manage_reperibilita(self):
        return self.has_permission('can_manage_reperibilita')
    
    def can_view_reperibilita(self):
        return self.has_permission('can_view_reperibilita')
    
    def can_manage_coverage(self):
        """Permesso per gestire coperture reperibilità"""
        return self.has_permission('can_manage_coverage')
    
    def can_view_coverage(self):
        """Permesso per visualizzare coperture reperibilità"""
        return self.has_permission('can_view_coverage')
    
    def can_access_reperibilita_menu(self):
        """Permesso per accedere al menu reperibilità"""
        return (self.can_manage_reperibilita() or self.can_view_reperibilita() or 
                self.can_manage_coverage() or self.can_view_coverage() or 
                self.can_view_interventions())
    
    # === PRESENZE ===
    def can_manage_attendance(self):
        return self.has_permission('can_manage_attendance')
    
    def can_view_attendance(self):
        return self.has_permission('can_view_attendance')
    
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
    
    # === INTERVENTI ===
    def can_manage_interventions(self):
        return self.has_permission('can_manage_interventions')
    
    def can_view_interventions(self):
        return self.has_permission('can_view_interventions')
    
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
        return self.can_manage_interventions() or self.can_view_interventions()
    
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
    



class AttendanceEvent(db.Model):
    """Modello per registrare eventi multipli di entrata/uscita nella stessa giornata"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    event_type = db.Column(db.String(20), nullable=False)  # 'clock_in', 'clock_out', 'break_start', 'break_end'
    timestamp = db.Column(db.DateTime, nullable=False)
    notes = db.Column(db.Text)
    shift_status = db.Column(db.String(20), nullable=True)  # 'anticipo', 'normale', 'ritardo' per entrate/uscite
    created_at = db.Column(db.DateTime, default=italian_now)
    
    user = db.relationship('User', backref='attendance_events')
    
    @staticmethod
    def get_user_status(user_id, target_date=None):
        """Restituisce lo stato attuale dell'utente (dentro/fuori/in pausa)"""
        if target_date is None:
            target_date = date.today()
            
        events = AttendanceEvent.query.filter(
            AttendanceEvent.user_id == user_id,
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
            # Import db here to avoid circular imports
            from app import db
            
            # Use raw SQL to avoid SQLAlchemy object encoding issues
            from sqlalchemy import text
            result = db.session.execute(
                text("SELECT event_type, timestamp FROM attendance_event WHERE user_id = :user_id AND date = :target_date ORDER BY timestamp"),
                {"user_id": user_id, "target_date": target_date}
            )
            
            events = []
            for row in result:
                events.append({
                    'event_type': row[0],
                    'timestamp': row[1]
                })
            
            if not events:
                return 0
        except Exception as e:
            # Log error and return 0 hours if query fails
            print(f"Error in get_daily_work_hours query: {e}")
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
            
        events = AttendanceEvent.query.filter(
            AttendanceEvent.user_id == user_id,
            AttendanceEvent.date == target_date
        ).order_by(AttendanceEvent.timestamp).all()
        
        # Crea lista di eventi con timestamp convertiti senza modificare gli originali
        converted_events = []
        for event in events:
            # Crea un oggetto semplice con i dati necessari
            event_data = type('Event', (), {
                'id': event.id,
                'user_id': event.user_id,
                'date': event.date,
                'event_type': event.event_type,
                'timestamp': convert_to_italian_time(event.timestamp),
                'notes': event.notes,
                'created_at': event.created_at,
                'user': event.user
            })()
            converted_events.append(event_data)
        
        return converted_events
    
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
                first_clock_in = convert_to_italian_time(event.timestamp)
            elif event.event_type == 'clock_out':
                last_clock_out = convert_to_italian_time(event.timestamp)
            elif event.event_type == 'break_start' and first_break_start is None:
                first_break_start = convert_to_italian_time(event.timestamp)
            elif event.event_type == 'break_end':
                last_break_end = convert_to_italian_time(event.timestamp)
        
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
        events = AttendanceEvent.query.filter(
            AttendanceEvent.user_id == user_id,
            AttendanceEvent.date >= start_date,
            AttendanceEvent.date <= end_date
        ).order_by(AttendanceEvent.date.asc(), AttendanceEvent.timestamp.asc()).all()
        
        # Raggruppa eventi per data
        events_by_date = {}
        for event in events:
            if event.date not in events_by_date:
                events_by_date[event.date] = []
            events_by_date[event.date].append(event)
        
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
        
        query = AttendanceEvent.query
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

class LeaveType(db.Model):
    """Modello per la gestione delle tipologie di permesso configurabili dall'amministratore"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    requires_approval = db.Column(db.Boolean, default=True)  # Se richiede autorizzazione
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=italian_now)
    updated_at = db.Column(db.DateTime, default=italian_now, onupdate=italian_now)
    
    # Relazione con le richieste di permesso
    leave_requests = db.relationship('LeaveRequest', backref='leave_type_ref', lazy='dynamic')
    
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
    
    # Campi per permessi orari
    start_time = db.Column(db.Time, nullable=True)  # Orario inizio per permessi parziali
    end_time = db.Column(db.Time, nullable=True)    # Orario fine per permessi parziali
    
    user = db.relationship('User', foreign_keys=[user_id], backref='leave_requests')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_leaves')
    
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
        if self.leave_type_ref:
            return self.leave_type_ref.name
        # Fallback per retrocompatibilità
        return self.leave_type or 'Tipo non specificato'
    
    def requires_approval(self):
        """Verifica se il permesso richiede approvazione"""
        if self.leave_type_ref:
            return self.leave_type_ref.requires_approval
        # Fallback: malattia non richiede approvazione, resto sì
        return self.leave_type != 'Malattia' if self.leave_type else True

class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    shift_type = db.Column(db.String(50), nullable=False, default='Turno')  # Simplified shift type
    created_at = db.Column(db.DateTime, default=italian_now)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
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
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=italian_now)
    updated_at = db.Column(db.DateTime, default=italian_now, onupdate=italian_now)

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
        for coverage in self.coverages.filter_by(is_active=True):
            total_hours += coverage.get_duration_hours()
        return total_hours
    
    def get_covered_days_count(self):
        """Conta i giorni della settimana con copertura"""
        covered_days = set()
        for coverage in self.coverages.filter_by(is_active=True):
            covered_days.add(coverage.day_of_week)
        return len(covered_days)
    
    def get_involved_roles(self):
        """Restituisce tutti i ruoli coinvolti nella copertura"""
        all_roles = set()
        for coverage in self.coverages.filter_by(is_active=True):
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
    is_active = db.Column(db.Boolean, default=True)
    # Campi per backward compatibility - periodo di validità per coperture senza template
    start_date = db.Column(db.Date, nullable=True)  # Data inizio validità (ora nullable)
    end_date = db.Column(db.Date, nullable=True)    # Data fine validità (ora nullable)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=italian_now)

    creator = db.relationship('User', backref='presidio_coverages')

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
                    self.is_active and self.template.is_active)
        elif self.start_date and self.end_date:
            # Backward compatibility: usa i campi diretti se non c'è template
            return self.start_date <= check_date <= self.end_date and self.is_active
        return self.is_active  # Se non ci sono date, considera solo is_active
    
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
    return PresidioCoverageTemplate.query.filter_by(is_active=True).order_by(
        PresidioCoverageTemplate.start_date.desc()
    ).all()

def get_presidio_coverage_for_day(day_of_week, target_date=None):
    """Ottieni coperture presidio per un giorno specifico"""
    query = PresidioCoverage.query.filter(
        PresidioCoverage.day_of_week == day_of_week,
        PresidioCoverage.is_active == True
    )
    
    if target_date:
        # Filtra per template validi nella data specifica
        query = query.join(PresidioCoverageTemplate).filter(
            PresidioCoverageTemplate.start_date <= target_date,
            PresidioCoverageTemplate.end_date >= target_date,
            PresidioCoverageTemplate.is_active == True
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


class ReperibilitaCoverage(db.Model):
    """Definisce la copertura reperibilità per giorno della settimana e fascia oraria con periodo di validità"""
    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Lunedì, 1=Martedì, ..., 6=Domenica, 7=Festivi
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    required_roles = db.Column(db.Text, nullable=False)  # JSON array dei ruoli richiesti per questa fascia
    sedi_ids = db.Column(db.Text, nullable=False)  # JSON array degli ID delle sedi coinvolte
    description = db.Column(db.String(200))  # Descrizione opzionale della copertura
    is_active = db.Column(db.Boolean, default=True)
    
    # Periodo di validità
    start_date = db.Column(db.Date, nullable=False)  # Data inizio validità
    end_date = db.Column(db.Date, nullable=False)    # Data fine validità
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=italian_now)
    
    creator = db.relationship('User', backref='reperibilita_coverages')
    
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
        return self.start_date <= check_date <= self.end_date and self.is_active
    
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
    
    user = db.relationship('User', foreign_keys=[user_id], backref='reperibilita_shifts')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_reperibilita_shifts')
    
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
    
    # Relationships
    user = db.relationship('User', backref='reperibilita_interventions')
    shift = db.relationship('ReperibilitaShift', backref='interventions')
    
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
    
    creator = db.relationship('User', backref='reperibilita_templates')


class Holiday(db.Model):
    """Festività gestibili dagli amministratori - nazionali e per sede"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    month = db.Column(db.Integer, nullable=False)  # 1-12
    day = db.Column(db.Integer, nullable=False)    # 1-31
    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=True)  # NULL = nazionale
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=italian_now)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    creator = db.relationship('User', backref='created_holidays')
    sede = db.relationship('Sede', backref='holidays')
    
    def __repr__(self):
        scope = f" ({self.sede.name})" if self.sede else " (Nazionale)"
        return f'<Holiday {self.name}: {self.day}/{self.month}{scope}>'
    
    @property
    def date_display(self):
        """Formato visualizzazione data"""
        return f"{self.day:02d}/{self.month:02d}"
    
    @property
    def scope_display(self):
        """Visualizza l'ambito della festività"""
        return self.sede.name if self.sede else "Nazionale"
    
    def is_holiday_on_date(self, check_date):
        """Verifica se questa festività cade nella data specificata"""
        return (check_date.month == self.month and 
                check_date.day == self.day and 
                self.is_active)
    
    @classmethod
    def get_holidays_for_date(cls, check_date, sede_id=None):
        """Ottiene tutte le festività per una data specifica e sede"""
        query = cls.query.filter(
            cls.month == check_date.month,
            cls.day == check_date.day,
            cls.is_active == True
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
    
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    related_leave_request = db.relationship('LeaveRequest', backref='messages')
    
    def __repr__(self):
        return f'<InternalMessage {self.title} to {self.recipient.username}>'
    
    def get_sender_name(self):
        """Restituisce il nome del mittente o 'Sistema' se è un messaggio automatico"""
        return self.sender.get_full_name() if self.sender else 'Sistema'



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


class ExpenseCategory(db.Model):
    """Categorie per le note spese"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=italian_now)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
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
        notification = InternalMessage(
            recipient_id=self.employee_id,
            sender_id=self.approved_by,
            title=title,
            message=message,
            message_type=message_type
        )
        
        db.session.add(notification)
    
    @classmethod
    def get_monthly_total(cls, employee_id, year, month, status='approved'):
        """Calcola il totale mensile delle note spese per un dipendente"""
        from sqlalchemy import extract, func
        
        result = db.session.query(func.sum(cls.amount)).filter(
            cls.employee_id == employee_id,
            cls.status == status,
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
            cls.status == status,
            extract('year', cls.expense_date) == year
        ).scalar()
        
        return result or 0
    

# ============================================================================
# SISTEMA STRAORDINARI
# ============================================================================

class OvertimeType(db.Model):
    """Tipologie di straordinario"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    hourly_rate_multiplier = db.Column(db.Float, default=1.5)  # Moltiplicatore per la paga oraria
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=italian_now)
    
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
            notification = InternalMessage(
                recipient_id=self.employee_id,
                sender_id=self.approved_by,
                title=title,
                message=message,
                message_type=message_type
            )
            
            db.session.add(notification)
                
        except Exception as e:
            print(f"Errore nell'invio della notifica straordinario: {e}")

    @classmethod
    def get_monthly_hours(cls, employee_id, year, month, status='approved'):
        """Calcola il totale mensile delle ore di straordinario per un dipendente"""
        from sqlalchemy import extract, func
        
        requests = db.session.query(cls).filter(
            cls.employee_id == employee_id,
            cls.status == status,
            extract('year', cls.overtime_date) == year,
            extract('month', cls.overtime_date) == month
        ).all()
        
        total_hours = sum(request.duration_hours for request in requests)
        return round(total_hours, 2)


class Sede(db.Model):
    """Modello per le sedi aziendali"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    address = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)
    tipologia = db.Column(db.String(20), nullable=False, default='Oraria')  # 'Oraria' o 'Turni'
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=italian_now)
    
    # Relationships (users già definito tramite backref in User)
    work_schedules = db.relationship('WorkSchedule', backref='sede_obj', lazy='dynamic')
    
    def __repr__(self):
        return f'<Sede {self.name}>'
    
    def get_active_schedules(self):
        """Restituisce gli orari di lavoro attivi per questa sede"""
        return self.work_schedules.filter_by(active=True).all()
    
    def has_turni_schedule(self):
        """Verifica se la sede ha un orario di tipo 'Turni'"""
        return self.work_schedules.filter_by(name='Turni', active=True).first() is not None
    
    def get_or_create_turni_schedule(self):
        """Ottiene o crea l'orario di tipo 'Turni' per questa sede"""
        from datetime import time
        turni_schedule = self.work_schedules.filter_by(name='Turni', active=True).first()
        
        if not turni_schedule and self.is_turni_mode():
            # Crea automaticamente l'orario 'Turni' per sedi con modalità turni
            turni_schedule = WorkSchedule()
            turni_schedule.sede_id = self.id
            turni_schedule.name = 'Turni'
            turni_schedule.start_time_min = time(0, 0)    # 00:00
            turni_schedule.start_time_max = time(23, 59)  # 23:59
            turni_schedule.end_time_min = time(0, 0)      # 00:00  
            turni_schedule.end_time_max = time(23, 59)    # 23:59
            turni_schedule.start_time = time(0, 0)        # Compatibilità
            turni_schedule.end_time = time(23, 59)        # Compatibilità
            turni_schedule.days_of_week = [0, 1, 2, 3, 4, 5, 6]  # Tutti i giorni
            turni_schedule.description = 'Orario flessibile per turnazioni'
            turni_schedule.active = True
            db.session.add(turni_schedule)
            db.session.commit()
        
        return turni_schedule
    
    def is_turni_mode(self):
        """Restituisce True se la sede opera con modalità turni"""
        return self.tipologia == 'Turni'
    
    def is_oraria_mode(self):
        """Restituisce True se la sede opera con modalità oraria"""
        return self.tipologia == 'Oraria'


class WorkSchedule(db.Model):
    """Modello per gli orari di lavoro per ogni sede"""
    id = db.Column(db.Integer, primary_key=True)
    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=False)
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
    
    # Constraint per evitare duplicati nella stessa sede
    __table_args__ = (db.UniqueConstraint('sede_id', 'name', name='_sede_schedule_name_uc'),)
    
    def __repr__(self):
        return f'<WorkSchedule {self.name} at {self.sede_obj.name if self.sede_obj else "Unknown Sede"}>'
    
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