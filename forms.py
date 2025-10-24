# =============================================================================
# FORMS.PY - LIFE WORKFORCE MANAGEMENT SYSTEM
# Comprehensive WTForms collection organized in logical sections for
# maintaining a scalable and organized form management system.
#
# SECTIONS (39 forms total):
# 1. Authentication & User Management (8 forms)
# 2. Attendance & Time Tracking (3 forms)
# 3. Leave Management (6 forms) 
# 4. Shift Management (4 forms)
# 5. Presidio Coverage Forms (4 forms)
# 6. Reperibilità Forms (4 forms)
# 7. Holiday Management Forms (1 form)
# 8. Internal Messaging Forms (1 form)
# 9. Expense Management Forms (3 forms)
# 10. Administrative Forms (4 forms)
# 11. Overtime Management Forms (4 forms)
# 12. Mileage Reimbursement Forms (5 forms)
# 13. ACI Tables Management Forms (2 forms)
# =============================================================================

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SelectMultipleField, FloatField, DateField, TimeField, TextAreaField, SubmitField, BooleanField, IntegerField, DecimalField, ValidationError
from wtforms.validators import DataRequired, Email, Length, NumberRange, EqualTo, Optional
from models import User, Sede, UserRole
from flask_wtf.file import FileField, FileAllowed
from utils_tenant import filter_by_company
import re


# =============================================================================
# CUSTOM VALIDATORS & HELPERS
# =============================================================================

def coerce_nullable_int(value):
    """
    Coerce function for SelectField that handles nullable integer values.
    Converts empty strings to None instead of raising ValueError.
    Used for optional foreign key fields like sede_id.
    """
    if value == '' or value is None:
        return None
    return int(value)


class StrongPassword:
    """
    Validatore per password robuste con requisiti di sicurezza.
    
    Requisiti:
    - Minimo 8 caratteri
    - Almeno una lettera maiuscola
    - Almeno una lettera minuscola
    - Almeno un numero
    - Almeno un carattere speciale (@#$%^&+=!*()_-.)
    """
    
    def __init__(self, message=None):
        if not message:
            message = (
                'La password deve contenere almeno: '
                '8 caratteri, una maiuscola, una minuscola, '
                'un numero e un carattere speciale (@#$%^&+=!*()_-.)'
            )
        self.message = message
    
    def __call__(self, form, field):
        password = field.data
        
        if not password:
            return  # Lascia che DataRequired gestisca i campi vuoti
        
        # Controlla lunghezza minima
        if len(password) < 8:
            raise ValidationError('La password deve essere di almeno 8 caratteri')
        
        # Controlla presenza di maiuscola
        if not re.search(r'[A-Z]', password):
            raise ValidationError('La password deve contenere almeno una lettera maiuscola')
        
        # Controlla presenza di minuscola
        if not re.search(r'[a-z]', password):
            raise ValidationError('La password deve contenere almeno una lettera minuscola')
        
        # Controlla presenza di numero
        if not re.search(r'\d', password):
            raise ValidationError('La password deve contenere almeno un numero')
        
        # Controlla presenza di carattere speciale
        if not re.search(r'[@#$%^&+=!*()_\-.]', password):
            raise ValidationError('La password deve contenere almeno un carattere speciale (@#$%^&+=!*()_-.)')


# =============================================================================
# AUTHENTICATION FORMS
# =============================================================================

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Ricordami')
    submit = SubmitField('Accedi')

class UserProfileForm(FlaskForm):
    """Form per modificare il proprio profilo utente"""
    first_name = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    last_name = StringField('Cognome', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    username = StringField('Username', render_kw={'readonly': True})
    profile_image = FileField('Immagine Profilo', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Solo immagini JPG, PNG o GIF!')
    ])
    
    # CIRCLE Social fields
    bio = TextAreaField('Biografia', validators=[Optional(), Length(max=500)], 
                       render_kw={'rows': 3, 'placeholder': 'Parlaci di te...'})
    job_title = StringField('Ruolo Aziendale', validators=[Optional(), Length(max=100)],
                           render_kw={'placeholder': 'Es: Software Developer'})
    department = StringField('Dipartimento', validators=[Optional(), Length(max=100)],
                            render_kw={'placeholder': 'Es: IT, HR, Sales...'})
    phone_number = StringField('Telefono Aziendale', validators=[Optional(), Length(max=20)],
                               render_kw={'placeholder': '+39 123 456 7890'})
    
    # Social Media Links
    linkedin_url = StringField('LinkedIn', validators=[Optional(), Length(max=255)],
                              render_kw={'placeholder': 'https://linkedin.com/in/...'})
    twitter_url = StringField('Twitter/X', validators=[Optional(), Length(max=255)],
                             render_kw={'placeholder': 'https://twitter.com/...'})
    instagram_url = StringField('Instagram', validators=[Optional(), Length(max=255)],
                               render_kw={'placeholder': 'https://instagram.com/...'})
    facebook_url = StringField('Facebook', validators=[Optional(), Length(max=255)],
                              render_kw={'placeholder': 'https://facebook.com/...'})
    github_url = StringField('GitHub', validators=[Optional(), Length(max=255)],
                            render_kw={'placeholder': 'https://github.com/...'})
    
    password = PasswordField('Nuova Password', validators=[Optional(), StrongPassword()])
    confirm_password = PasswordField('Conferma Password', validators=[
        EqualTo('password', message='Le password devono corrispondere')
    ])
    submit = SubmitField('Salva Modifiche')

    def __init__(self, original_email=None, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        self.original_email = original_email

    def validate_email(self, email):
        if email.data != self.original_email:
            from flask_login import current_user
            # Check email uniqueness within the same company (multi-tenant)
            user = User.query.filter_by(
                email=email.data,
                company_id=current_user.company_id
            ).first()
            if user:
                raise ValidationError('Questa email è già in uso.')

# =============================================================================
# USER MANAGEMENT FORMS
# =============================================================================

class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password')
    role = SelectField('Ruolo', choices=[], validators=[DataRequired()])
    first_name = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    last_name = StringField('Cognome', validators=[DataRequired(), Length(max=100)])
    sede = SelectField('Sede', coerce=int, validators=[], validate_choice=False)
    all_sedi = BooleanField('Accesso a tutte le sedi', default=False)
    work_schedule = SelectField('Orario di Lavoro', coerce=lambda x: int(x) if x and x != '' else None, validators=[Optional()], validate_choice=False)
    aci_vehicle_tipo = SelectField('Tipo Veicolo', coerce=str, validators=[Optional()], validate_choice=False)
    aci_vehicle_marca = SelectField('Marca', coerce=str, validators=[Optional()], validate_choice=False)
    aci_vehicle = SelectField('Modello', coerce=lambda x: int(x) if x and x != '' else None, validators=[Optional()], validate_choice=False)
    part_time_percentage = StringField('Percentuale di Lavoro (%)', 
                                     default='100.0')
    overtime_enabled = BooleanField('Abilitato a Straordinari', default=False)
    overtime_type = SelectField('Tipologia Straordinario', 
                              choices=[('', 'Seleziona...'), 
                                       ('Straordinario Pagato', 'Straordinario Pagato'), 
                                       ('Banca Ore', 'Banca Ore')],
                              validators=[Optional()])
    banca_ore_limite_max = StringField('Limite Massimo Ore', 
                                     default='40.0')
    banca_ore_periodo_mesi = StringField('Periodo Validità (mesi)', 
                                       default='12')
    active = BooleanField('Attivo', default=True)
    submit = SubmitField('Salva Utente')
    
    def __init__(self, original_username=None, is_edit=False, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.is_edit = is_edit
        
        # Popola le scelte delle sedi
        try:
            from models import Sede as SedeModel, ACITable
            sedi_attive = SedeModel.query.filter_by(active=True).all()
            self.sede.choices = [(-1, 'Seleziona una sede')] + [(sede.id, sede.name) for sede in sedi_attive]
            
            # Popola le scelte dei veicoli ACI con filtri progressivi
            aci_vehicles = ACITable.query.order_by(ACITable.tipologia, ACITable.marca, ACITable.modello).all()
            
            # Tipo veicolo
            tipos = list(set([v.tipologia for v in aci_vehicles if v.tipologia]))
            self.aci_vehicle_tipo.choices = [('', 'Seleziona tipo')] + [(tipo, tipo) for tipo in sorted(tipos)]
            
            # Marca (inizialmente vuoto, sarà popolato via JavaScript)
            self.aci_vehicle_marca.choices = [('', 'Seleziona prima il tipo')]
            
            # Modello (inizialmente vuoto, sarà popolato via JavaScript)
            self.aci_vehicle.choices = [('', 'Seleziona prima marca')]
        except:
            self.sede.choices = [(-1, 'Seleziona una sede')]
        
        # Inizializza choices degli orari (verrà popolato dinamicamente via JavaScript)
        self.work_schedule.choices = [('', 'Nessun orario specifico')]
        
        # Se in modalità edit e c'è un work_schedule_id, aggiungi l'orario corrente alle scelte
        obj = kwargs.get('obj')
        if is_edit and obj and hasattr(obj, 'work_schedule_id') and obj.work_schedule_id:
            try:
                from models import WorkSchedule
                current_schedule = WorkSchedule.query.get(obj.work_schedule_id)
                if current_schedule:
                    schedule_choice = (current_schedule.id, f"{current_schedule.name} ({current_schedule.start_time.strftime('%H:%M') if current_schedule.start_time else ''}-{current_schedule.end_time.strftime('%H:%M') if current_schedule.end_time else ''})")
                    if schedule_choice not in self.work_schedule.choices:
                        self.work_schedule.choices.append(schedule_choice)
            except Exception as e:
                # Work schedule loading error - fallback to empty choices
                pass
        
        # Popola le scelte dei ruoli dinamicamente
        try:
            from utils_tenant import filter_by_company
            ruoli_attivi = filter_by_company(UserRole.query).filter_by(active=True).all()
            self.role.choices = [(role.name, role.display_name) for role in ruoli_attivi]
            # Se non ci sono ruoli personalizzati, inizializza con lista vuota
            if not self.role.choices:
                self.role.choices = []
        except:
            self.role.choices = []
        
        # Set password validators based on mode
        if not is_edit:
            self.password.validators = [DataRequired(), StrongPassword()]
        else:
            # In edit mode, password is optional but if provided must be strong
            self.password.validators = [Optional(), StrongPassword()]
    
    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Username già esistente. Scegli un altro username.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user and (not self.original_username or user.username != self.original_username):
            raise ValidationError('Email già esistente. Scegli un\'altra email.')
    
    def validate_sede(self, sede):
        # Se all_sedi è True, la sede specifica non è richiesta
        if self.all_sedi.data:
            return
        # Se all_sedi è False, deve essere selezionata una sede specifica
        if not sede.data or sede.data == -1:
            raise ValidationError('Seleziona una sede o abilita "Accesso a tutte le sedi".')
    
    def validate_work_schedule(self, work_schedule):
        # Il work_schedule è opzionale, ma se selezionato deve essere valido
        if work_schedule.data and work_schedule.data is not None:
            # Verifica che esista un orario con quell'ID
            from models import WorkSchedule
            schedule = WorkSchedule.query.get(work_schedule.data)
            if not schedule:
                raise ValidationError('Orario di lavoro selezionato non valido.')
            # Se c'è una sede selezionata, verifica che l'orario appartenga a quella sede
            if self.sede.data and self.sede.data > 0:
                if schedule.sede_id != self.sede.data:
                    raise ValidationError('L\'orario di lavoro deve appartenere alla sede selezionata.')
    
    def validate_password(self, password):
        # For new users, password is required
        if not self.is_edit and not password.data:
            raise ValidationError('Password è obbligatoria per i nuovi utenti.')
        
        # If password is provided (new or edit), check minimum length
        if password.data and len(password.data) < 6:
            raise ValidationError('La password deve essere lunga almeno 6 caratteri.')
    
    def validate_part_time_percentage(self, part_time_percentage):
        if part_time_percentage.data:
            try:
                # Replace comma with dot for proper float conversion
                value = float(part_time_percentage.data.replace(',', '.'))
                if not (1 <= value <= 100):
                    raise ValidationError('La percentuale deve essere tra 1 e 100.')
            except (ValueError, AttributeError):
                raise ValidationError('Inserire un numero valido.')
    
    def get_part_time_percentage_as_float(self):
        """Convert the percentage string to float for database storage"""
        if self.part_time_percentage.data:
            try:
                return float(self.part_time_percentage.data.replace(',', '.'))
            except (ValueError, AttributeError):
                return 100.0
        return 100.0
    
    def get_banca_ore_limite_max_as_float(self):
        """Convert the banca ore limite max string to float for database storage"""
        if self.banca_ore_limite_max.data:
            try:
                return float(self.banca_ore_limite_max.data.replace(',', '.'))
            except (ValueError, AttributeError):
                return 40.0
        return 40.0
    
    def get_banca_ore_periodo_mesi_as_int(self):
        """Convert the banca ore periodo mesi string to int for database storage"""
        if self.banca_ore_periodo_mesi.data:
            try:
                return int(self.banca_ore_periodo_mesi.data)
            except (ValueError, AttributeError):
                return 12
        return 12

# =============================================================================
# ATTENDANCE FORMS
# =============================================================================

class AttendanceForm(FlaskForm):
    sede_id = SelectField('Sede', coerce=lambda x: int(x) if x and x != '' else None, validators=[Optional()])
    notes = TextAreaField('Note')
    submit = SubmitField('Registra')
    
    def __init__(self, user=None, *args, **kwargs):
        super(AttendanceForm, self).__init__(*args, **kwargs)
        if user and user.all_sedi:
            # Per utenti multi-sede, popola le sedi disponibili
            from models import Sede
            sedi = Sede.query.filter_by(active=True).all()
            self.sede_id.choices = [('', 'Seleziona una sede')] + [(sede.id, sede.name) for sede in sedi]
            # Rendi obbligatorio per utenti multi-sede
            self.sede_id.validators = [DataRequired(message="Seleziona una sede")]
        elif user and user.sede_id:
            # Per utenti con sede specifica, usa quella sede
            self.sede_id.choices = [(user.sede_id, user.sede_obj.name if user.sede_obj else 'Sede')]
            self.sede_id.data = user.sede_id
        else:
            # Nascondi il campo se non applicabile
            self.sede_id.choices = []

# =============================================================================
# LEAVE MANAGEMENT FORMS
# =============================================================================

class LeaveTypeForm(FlaskForm):
    """Form per la gestione delle tipologie di permesso"""
    name = StringField('Nome Tipologia', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Descrizione', validators=[Length(max=500)])
    requires_approval = BooleanField('Richiede Autorizzazione', default=True)
    active = BooleanField('Attiva', default=True)
    submit = SubmitField('Salva Tipologia')
    
    def __init__(self, original_name=None, *args, **kwargs):
        super(LeaveTypeForm, self).__init__(*args, **kwargs)
        self.original_name = original_name
    
    def validate_name(self, name):
        if name.data != self.original_name:
            from models import LeaveType
            existing_type = LeaveType.query.filter_by(name=name.data).first()
            if existing_type:
                raise ValidationError('Esiste già una tipologia con questo nome.')

class LeaveRequestForm(FlaskForm):
    leave_type_id = SelectField('Tipo Richiesta', coerce=lambda x: int(x) if x and x != '' else None, validators=[DataRequired()])
    
    # Campi per date (sempre presenti)
    start_date = DateField('Data Inizio', validators=[DataRequired()])
    end_date = DateField('Data Fine', validators=[Optional()])
    
    # Campi per orari (solo per permessi)
    start_time = TimeField('Ora Inizio', validators=[Optional()])
    end_time = TimeField('Ora Fine', validators=[Optional()])
    
    # Campo motivo
    reason = TextAreaField('Motivo', validators=[Optional(), Length(max=500)], render_kw={'rows': 3, 'placeholder': 'Inserisci il motivo della richiesta (opzionale)'})
    
    # Campo banca ore
    use_banca_ore = BooleanField('Utilizza ore dalla Banca Ore', default=False)
    
    submit = SubmitField('Invia Richiesta')
    
    def __init__(self, *args, **kwargs):
        super(LeaveRequestForm, self).__init__(*args, **kwargs)
        # Popola le scelte delle tipologie di permesso attive
        try:
            from models import LeaveType
            active_types = LeaveType.query.filter_by(active=True).order_by(LeaveType.name).all()
            self.leave_type_id.choices = [(None, 'Seleziona tipo richiesta')] + [(t.id, t.name) for t in active_types]
        except:
            self.leave_type_id.choices = [(None, 'Seleziona tipo richiesta')]
    
    def validate_start_date(self, field):
        from datetime import date
        if field.data and field.data < date.today():
            raise ValidationError('La data di inizio non può essere nel passato.')
    
    def validate_end_date(self, end_date):
        from datetime import date
        if end_date.data and end_date.data < date.today():
            raise ValidationError('La data di fine non può essere nel passato.')
        if end_date.data and end_date.data < self.start_date.data:
            raise ValidationError('La data di fine deve essere successiva alla data di inizio.')
    
    def validate_start_time(self, start_time):
        # Validazione orari se necessaria per la tipologia selezionata
        if self.start_time.data and self.end_time.data:
            if self.end_time.data <= self.start_time.data:
                raise ValidationError('L\'ora di fine deve essere successiva all\'ora di inizio.')
                
    def get_selected_leave_type(self):
        """Restituisce l'oggetto LeaveType selezionato"""
        if self.leave_type_id.data:
            from models import LeaveType
            return LeaveType.query.get(self.leave_type_id.data)
        return None

# =============================================================================
# SHIFT MANAGEMENT FORMS
# =============================================================================

class ShiftForm(FlaskForm):
    user_id = SelectField('Utente', coerce=int, validators=[DataRequired()])
    date = DateField('Data', validators=[DataRequired()])
    start_time = TimeField('Ora Inizio', validators=[DataRequired()])
    end_time = TimeField('Ora Fine', validators=[DataRequired()])
    submit = SubmitField('Crea Turno')

class EditShiftForm(FlaskForm):
    """Form per modificare turni esistenti (utente e orari - non data né tipo)"""
    user_id = SelectField('Utente', coerce=int, validators=[DataRequired()])
    start_time = TimeField('Ora Inizio', validators=[DataRequired()])
    end_time = TimeField('Ora Fine', validators=[DataRequired()])
    submit = SubmitField('Salva Modifiche')
    
    def validate_end_time(self, end_time):
        if end_time.data <= self.start_time.data:
            raise ValidationError('L\'ora di fine deve essere successiva all\'ora di inizio')

class ShiftTemplateForm(FlaskForm):
    name = StringField('Nome Template', validators=[DataRequired(), Length(max=100)])
    start_date = DateField('Data Inizio', validators=[DataRequired()])
    end_date = DateField('Data Fine', validators=[DataRequired()])
    description = TextAreaField('Descrizione')
    submit = SubmitField('Genera Turnazioni')
    
    def validate_end_date(self, end_date):
        if end_date.data < self.start_date.data:
            raise ValidationError('La data di fine deve essere successiva alla data di inizio.')


# =============================================================================
# PRESIDIO COVERAGE FORMS
# =============================================================================

class PresidioCoverageForm(FlaskForm):
    # Periodo di validità
    start_date = DateField('Data Inizio Validità', validators=[DataRequired()])
    end_date = DateField('Data Fine Validità', validators=[DataRequired()])
    
    days_of_week = SelectMultipleField('Giorni della Settimana', choices=[
        (0, 'Lunedì'),
        (1, 'Martedì'),
        (2, 'Mercoledì'),
        (3, 'Giovedì'),
        (4, 'Venerdì'),
        (5, 'Sabato'),
        (6, 'Domenica')
    ], coerce=int, validators=[DataRequired()], render_kw={'class': 'form-select', 'size': '7', 'multiple': True})
    start_time = TimeField('Ora Inizio', validators=[DataRequired()])
    end_time = TimeField('Ora Fine', validators=[DataRequired()])
    required_roles = SelectMultipleField('Ruoli Richiesti', choices=[], validators=[DataRequired()])
    description = StringField('Descrizione', validators=[Length(max=200)])
    active = BooleanField('Attivo', default=True)
    submit = SubmitField('Salva Copertura')
    
    def __init__(self, *args, **kwargs):
        super(PresidioCoverageForm, self).__init__(*args, **kwargs)
        # Popola i ruoli dinamicamente dal database, escludendo Admin
        from models import UserRole
        from utils_tenant import filter_by_company
        try:
            roles = filter_by_company(UserRole.query).filter(UserRole.name != 'Admin').all()
            self.required_roles.choices = [(role.name, role.name) for role in roles]
        except:
            # Fallback se il database non è disponibile
            self.required_roles.choices = [
                ('Management', 'Management'),
                ('Staff', 'Staff'),
                ('Redattore', 'Redattore'),
                ('Sviluppatore', 'Sviluppatore'),
                ('Operatore', 'Operatore'),
                ('Ente', 'Ente')
            ]

    def validate_end_time(self, end_time):
        if end_time.data <= self.start_time.data:
            raise ValidationError('L\'ora di fine deve essere successiva all\'ora di inizio')
    
    def validate_end_date(self, end_date):
        if end_date.data < self.start_date.data:
            raise ValidationError('La data di fine validità deve essere successiva alla data di inizio')


class PresidioReplicaForm(FlaskForm):
    """Form semplificato per replicare un presidio cambiando solo le date"""
    start_date = DateField('Data Inizio Nuovo Periodo', validators=[DataRequired()])
    end_date = DateField('Data Fine Nuovo Periodo', validators=[DataRequired()])
    submit = SubmitField('Replica Presidio')
    
    def validate_end_date(self, end_date):
        if end_date.data <= self.start_date.data:
            raise ValidationError('La data di fine deve essere successiva alla data di inizio')


# =============================================================================
# REPERIBILITÀ FORMS
# =============================================================================

class ReperibilitaCoverageForm(FlaskForm):
    """Form per creare/modificare coperture reperibilità"""
    start_date = DateField('Data Inizio Validità', validators=[DataRequired()])
    end_date = DateField('Data Fine Validità', validators=[DataRequired()])
    
    # Selezione sedi - supporta selezione multipla
    sedi = SelectMultipleField('Sedi Coinvolte', choices=[], validators=[DataRequired()], 
                              render_kw={'class': 'form-select', 'size': '5', 'multiple': True})
    
    # Giorni della settimana - supporta selezione multipla (include festivi)
    days_of_week = SelectMultipleField('Giorni della Settimana', choices=[
        (0, 'Lunedì'),
        (1, 'Martedì'),
        (2, 'Mercoledì'),
        (3, 'Giovedì'),
        (4, 'Venerdì'),
        (5, 'Sabato'),
        (6, 'Domenica'),
        (7, 'Festivi')
    ], coerce=int, validators=[DataRequired()], render_kw={'class': 'form-select', 'size': '8', 'multiple': True})
    
    start_time = TimeField('Ora Inizio', validators=[DataRequired()])
    end_time = TimeField('Ora Fine', validators=[DataRequired()])
    
    required_roles = SelectMultipleField('Ruoli Richiesti', choices=[], validators=[DataRequired()])
    description = StringField('Descrizione', validators=[Length(max=200)])
    active = BooleanField('Attivo', default=True)
    submit = SubmitField('Salva Copertura')
    
    def __init__(self, *args, **kwargs):
        super(ReperibilitaCoverageForm, self).__init__(*args, **kwargs)
        # Popola i ruoli dinamicamente dal database, escludendo Admin
        from models import UserRole, Sede
        from utils_tenant import filter_by_company
        try:
            # Popola ruoli escludendo Admin
            roles = filter_by_company(UserRole.query).filter(UserRole.name != 'Admin').all()
            self.required_roles.choices = [(role.name, role.name) for role in roles]
            
            # Popola sedi
            sedi = Sede.query.all()
            self.sedi.choices = [(str(sede.id), sede.name) for sede in sedi]
        except:
            # Fallback se il database non è disponibile
            self.required_roles.choices = [
                ('Management', 'Management'),
                ('Staff', 'Staff'),
                ('Redattore', 'Redattore'),
                ('Sviluppatore', 'Sviluppatore'),
                ('Operatore', 'Operatore'),
                ('Ente', 'Ente')
            ]
            self.sedi.choices = [('1', 'Sede Principale')]
    
    def validate_end_time(self, end_time):
        if end_time.data and self.start_time.data:
            # Allow overnight shifts for on-call duty
            pass
    
    def validate_end_date(self, end_date):
        if end_date.data and self.start_date.data and end_date.data < self.start_date.data:
            raise ValidationError('La data di fine deve essere successiva alla data di inizio.')


class ReperibilitaReplicaForm(FlaskForm):
    """Form per replicare una copertura reperibilità cambiando date e/o ruoli"""
    start_date = DateField('Data Inizio Nuovo Periodo', validators=[DataRequired()])
    end_date = DateField('Data Fine Nuovo Periodo', validators=[DataRequired()])
    sede_id = SelectField('Sede di Destinazione', choices=[], validators=[Optional()])
    
    # Mappatura ruoli: da ruolo originale a nuovo ruolo
    role_mapping = SelectMultipleField('Sostituzione Ruoli (Opzionale)', 
                                     choices=[
                                         ('Admin->Project Manager', 'Admin → Project Manager'),
                                         ('Admin->Redattore', 'Admin → Redattore'),
                                         ('Admin->Sviluppatore', 'Admin → Sviluppatore'),
                                         ('Admin->Operatore', 'Admin → Operatore'),
                                         ('Project Manager->Admin', 'Project Manager → Admin'),
                                         ('Project Manager->Redattore', 'Project Manager → Redattore'),
                                         ('Project Manager->Sviluppatore', 'Project Manager → Sviluppatore'),
                                         ('Project Manager->Operatore', 'Project Manager → Operatore'),
                                         ('Redattore->Admin', 'Redattore → Admin'),
                                         ('Redattore->Project Manager', 'Redattore → Project Manager'),
                                         ('Redattore->Sviluppatore', 'Redattore → Sviluppatore'),
                                         ('Redattore->Operatore', 'Redattore → Operatore'),
                                         ('Sviluppatore->Admin', 'Sviluppatore → Admin'),
                                         ('Sviluppatore->Project Manager', 'Sviluppatore → Project Manager'),
                                         ('Sviluppatore->Redattore', 'Sviluppatore → Redattore'),
                                         ('Sviluppatore->Operatore', 'Sviluppatore → Operatore'),
                                         ('Operatore->Admin', 'Operatore → Admin'),
                                         ('Operatore->Project Manager', 'Operatore → Project Manager'),
                                         ('Operatore->Redattore', 'Operatore → Redattore'),
                                         ('Operatore->Sviluppatore', 'Operatore → Sviluppatore')
                                     ], 
                                     render_kw={'class': 'form-select', 'size': '8', 'multiple': True})
    
    submit = SubmitField('Replica Reperibilità')
    
    def validate_end_date(self, end_date):
        if end_date.data and self.start_date.data and end_date.data < self.start_date.data:
            raise ValidationError('La data di fine deve essere successiva alla data di inizio.')
    
    def __init__(self, *args, **kwargs):
        super(ReperibilitaReplicaForm, self).__init__(*args, **kwargs)
        # Popola le sedi disponibili
        from models import Sede
        try:
            sedi = Sede.query.filter_by(active=True).order_by(Sede.name).all()
            self.sede_id.choices = [('', 'Mantieni sedi originali')] + [(str(sede.id), sede.name) for sede in sedi]
        except:
            self.sede_id.choices = [('', 'Mantieni sedi originali')]
    
    def get_role_mapping_dict(self):
        """Converte le selezioni in un dizionario di mappatura ruoli"""
        mapping = {}
        for selection in self.role_mapping.data:
            from_role, to_role = selection.split('->')
            mapping[from_role] = to_role
        return mapping


class ReperibilitaTemplateForm(FlaskForm):
    """Form per generare turnazioni reperibilità da coperture esistenti"""
    coverage_period = SelectField('Copertura Reperibilità', choices=[], validators=[DataRequired()])
    use_full_period = BooleanField('Usa intero periodo della copertura', default=True)
    start_date = DateField('Data Inizio Personalizzata', validators=[Optional()])
    end_date = DateField('Data Fine Personalizzata', validators=[Optional()])
    description = TextAreaField('Descrizione (opzionale)')
    submit = SubmitField('Genera Turnazioni Reperibilità')
    
    def __init__(self, *args, **kwargs):
        super(ReperibilitaTemplateForm, self).__init__(*args, **kwargs)
        # Popola le coperture dinamicamente dal database
        from models import ReperibilitaCoverage
        from datetime import date
        try:
            # Raggruppa le coperture per periodo (start_date + end_date)
            coverages = filter_by_company(ReperibilitaCoverage.query).filter(
                ReperibilitaCoverage.active == True,
                ReperibilitaCoverage.end_date >= date.today()
            ).all()
            
            # Crea un dizionario raggruppato per periodo + sede per separare duplicazioni
            periods = {}
            for coverage in coverages:
                # Include sede nel period_key per separare coperture duplicate con sedi diverse
                sede_ids = sorted(coverage.get_sedi_ids_list())
                sede_key = "_".join(map(str, sede_ids)) if sede_ids else "no_sede"
                period_key = f"{coverage.start_date.strftime('%Y-%m-%d')}__{coverage.end_date.strftime('%Y-%m-%d')}__{sede_key}"
                
                if period_key not in periods:
                    periods[period_key] = {
                        'start_date': coverage.start_date,
                        'end_date': coverage.end_date,
                        'coverages': []
                    }
                periods[period_key]['coverages'].append(coverage)
            
            # Crea le scelte per il SelectField
            choices = []
            for period_key, data in periods.items():
                sedi_names = set()
                for c in data['coverages']:
                    sedi_names.update([name for name in c.get_sedi_names().split(', ') if name != 'Nessuna sede'])
                
                sedi_text = ', '.join(sorted(sedi_names)) if sedi_names else 'Tutte le sedi'
                label = f"{data['start_date'].strftime('%d/%m/%Y')} - {data['end_date'].strftime('%d/%m/%Y')} ({sedi_text})"
                choices.append((period_key, label))
            
            self.coverage_period.choices = sorted(choices, key=lambda x: x[1])
            
        except:
            # Fallback se il database non è disponibile
            self.coverage_period.choices = [('', 'Nessuna copertura disponibile')]
    
    def validate_end_date(self, end_date):
        # Validazione solo se non si usa l'intero periodo
        if not self.use_full_period.data:
            if not end_date.data:
                raise ValidationError('Specifica una data di fine personalizzata.')
            if self.start_date.data and end_date.data < self.start_date.data:
                raise ValidationError('La data di fine deve essere successiva alla data di inizio.')
    
    def validate_start_date(self, start_date):
        # Validazione solo se non si usa l'intero periodo
        if not self.use_full_period.data and not start_date.data:
            raise ValidationError('Specifica una data di inizio personalizzata.')


# =============================================================================
# HOLIDAY MANAGEMENT FORMS
# =============================================================================

class HolidayForm(FlaskForm):
    """Form per gestire festività"""
    name = StringField('Nome Festività', validators=[DataRequired(), Length(max=100)])
    day = SelectField('Giorno', choices=[(i, str(i)) for i in range(1, 32)], 
                      coerce=int, validators=[DataRequired()])
    month = SelectField('Mese', choices=[
        (1, 'Gennaio'), (2, 'Febbraio'), (3, 'Marzo'), (4, 'Aprile'),
        (5, 'Maggio'), (6, 'Giugno'), (7, 'Luglio'), (8, 'Agosto'),
        (9, 'Settembre'), (10, 'Ottobre'), (11, 'Novembre'), (12, 'Dicembre')
    ], coerce=int, validators=[DataRequired()])
    sede_id = SelectField('Ambito', coerce=lambda x: int(x) if x and x != '' else None, 
                         validators=[Optional()])
    description = StringField('Descrizione', validators=[Length(max=200)])
    active = BooleanField('Attiva', default=True)
    submit = SubmitField('Salva Festività')
    
    def __init__(self, *args, **kwargs):
        super(HolidayForm, self).__init__(*args, **kwargs)
        
        # Popola le sedi disponibili
        from models import Sede
        sedi = Sede.query.filter_by(active=True).order_by(Sede.name).all()
        self.sede_id.choices = [('', 'Nazionale (tutte le sedi)')] + [(s.id, s.name) for s in sedi]
    
    def validate_day(self, day):
        """Valida che il giorno sia valido per il mese selezionato"""
        if self.month.data and day.data:
            # Validazione semplificata - febbraio può avere 29 giorni negli anni bisestili
            days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            if day.data > days_in_month[self.month.data - 1]:
                month_names = ['', 'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 
                              'Maggio', 'Giugno', 'Luglio', 'Agosto', 
                              'Settembre', 'Ottobre', 'Novembre', 'Dicembre']
                raise ValidationError(f'Il giorno {day.data} non è valido per {month_names[self.month.data]}')


class ChangePasswordForm(FlaskForm):
    """Form per cambiare password utente"""
    current_password = PasswordField('Password Attuale', validators=[DataRequired()])
    new_password = PasswordField('Nuova Password', validators=[
        DataRequired(), 
        StrongPassword()
    ])
    confirm_password = PasswordField('Conferma Nuova Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='Le password non corrispondono')
    ])
    submit = SubmitField('Cambia Password')


class ForgotPasswordForm(FlaskForm):
    """Form per richiedere reset password"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Invia Link Reset')


class ResetPasswordForm(FlaskForm):
    """Form per impostare nuova password dopo reset"""
    new_password = PasswordField('Nuova Password', validators=[
        DataRequired(), 
        StrongPassword()
    ])
    confirm_password = PasswordField('Conferma Nuova Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='Le password non corrispondono')
    ])
    submit = SubmitField('Imposta Nuova Password')


# =============================================================================
# INTERNAL MESSAGING FORMS
# =============================================================================

class SendMessageForm(FlaskForm):
    """Form per inviare messaggi interni"""
    recipient_ids = SelectMultipleField('Destinatari', coerce=int, validators=[DataRequired()])
    title = StringField('Oggetto', validators=[DataRequired(), Length(max=200)])
    message = TextAreaField('Messaggio', validators=[DataRequired()])
    message_type = SelectField('Tipo Messaggio', 
                              choices=[
                                  ('info', 'Informativo'),
                                  ('success', 'Successo'),
                                  ('warning', 'Attenzione'),
                                  ('danger', 'Urgente')
                              ],
                              default='info',
                              validators=[DataRequired()])
    submit = SubmitField('Invia Messaggio')
    
    def __init__(self, current_user=None, *args, **kwargs):
        super(SendMessageForm, self).__init__(*args, **kwargs)
        
        if current_user:
            # Seleziona utenti disponibili per l'invio messaggi
            # Filtra per company, stessa sede o accesso globale, escludi Admin/Staff
            users_query = filter_by_company(User.query).filter(
                User.active == True,
                User.id != current_user.id,  # Escludi se stesso
                ~User.role.in_(['Admin', 'Staff'])  # Escludi amministratori
            )
            
            if not current_user.all_sedi and current_user.sede_id:
                # Utente sede-specifico: solo utenti della stessa sede
                users_query = users_query.filter(User.sede_id == current_user.sede_id)
            
            # Se l'utente ha accesso a tutte le sedi, può inviare a tutti (della sua azienda)
            available_users = users_query.order_by(User.first_name, User.last_name).all()
            
            self.recipient_ids.choices = [
                (user.id, f"{user.get_full_name()} ({user.role})")
                for user in available_users
            ]
            
            if not self.recipient_ids.choices:
                self.recipient_ids.choices = [(0, 'Nessun utente disponibile')]


# =============================================================================
# EXPENSE MANAGEMENT FORMS
# =============================================================================

class ExpenseCategoryForm(FlaskForm):
    """Form per gestire le categorie di spesa"""
    name = StringField('Nome Categoria', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Descrizione', validators=[Length(max=255)])
    active = BooleanField('Attiva', default=True)
    submit = SubmitField('Salva Categoria')


class ExpenseReportForm(FlaskForm):
    """Form per creare/modificare note spese"""
    expense_date = DateField('Data Spesa', validators=[DataRequired()])
    description = TextAreaField('Descrizione', validators=[DataRequired(), Length(max=500)])
    amount = DecimalField('Importo (€)', validators=[DataRequired(), NumberRange(min=0.01, max=99999.99)], places=2)
    category_id = SelectField('Categoria', coerce=int, validators=[DataRequired()])
    receipt_file = FileField('Ricevuta/Documento', validators=[
        FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'Solo file PDF o immagini!')
    ])
    submit = SubmitField('Salva Nota Spese')
    
    def __init__(self, *args, **kwargs):
        super(ExpenseReportForm, self).__init__(*args, **kwargs)
        # Popola le categorie attive
        from models import ExpenseCategory
        categories = ExpenseCategory.query.filter_by(active=True).order_by(ExpenseCategory.name).all()
        self.category_id.choices = [(cat.id, cat.name) for cat in categories]
        
        if not self.category_id.choices:
            self.category_id.choices = [(0, 'Nessuna categoria disponibile')]








# Le classi straordinari sono definite correttamente alla fine del file


class ExpenseApprovalForm(FlaskForm):
    """Form per approvare/rifiutare note spese"""
    action = SelectField('Azione', choices=[
        ('approve', 'Approva'),
        ('reject', 'Rifiuta')
    ], validators=[DataRequired()])
    comment = TextAreaField('Commento', validators=[Length(max=500)])
    submit = SubmitField('Conferma')


class ExpenseFilterForm(FlaskForm):
    """Form per filtrare le note spese"""
    employee_id = SelectField('Dipendente', coerce=lambda x: int(x) if x and x != '' else None, validators=[Optional()])
    category_id = SelectField('Categoria', coerce=lambda x: int(x) if x and x != '' else None, validators=[Optional()])
    status = SelectField('Stato', choices=[
        ('', 'Tutti'),
        ('pending', 'In Attesa'),
        ('approved', 'Approvate'),
        ('rejected', 'Rifiutate')
    ], validators=[Optional()])
    date_from = DateField('Da Data', validators=[Optional()])
    date_to = DateField('A Data', validators=[Optional()])
    submit = SubmitField('Filtra')
    reset = SubmitField('Reset')
    
    def __init__(self, current_user=None, *args, **kwargs):
        super(ExpenseFilterForm, self).__init__(*args, **kwargs)
        
        # Popola dipendenti (solo se l'utente può vedere altri dipendenti)
        if current_user and (current_user.can_view_expense_reports() or current_user.can_approve_expense_reports()):
            from models import User
            
            users_query = User.query.filter(User.active == True)
            
            # Filtra per sede se necessario
            if not current_user.all_sedi and current_user.sede_id:
                users_query = users_query.filter(User.sede_id == current_user.sede_id)
            
            employees = users_query.order_by(User.first_name, User.last_name).all()
            self.employee_id.choices = [('', 'Tutti i dipendenti')] + [
                (emp.id, emp.get_full_name()) for emp in employees
            ]
        else:
            self.employee_id.choices = [('', 'Tutti i dipendenti')]
        
        # Popola categorie
        from models import ExpenseCategory
        categories = ExpenseCategory.query.filter_by(active=True).order_by(ExpenseCategory.name).all()
        self.category_id.choices = [('', 'Tutte le categorie')] + [
            (cat.id, cat.name) for cat in categories
        ]


# =============================================================================
# ADMINISTRATIVE FORMS
# =============================================================================

class SedeForm(FlaskForm):
    """Form per gestire le sedi aziendali"""
    name = StringField('Nome Sede', validators=[DataRequired(), Length(max=100)])
    address = StringField('Indirizzo', validators=[Length(max=200)])
    description = TextAreaField('Descrizione', validators=[Length(max=500)])
    tipologia = SelectField('Tipologia Sede', choices=[
        ('Oraria', 'Oraria - Gestione basata su orari'),
        ('Turni', 'Turni - Gestione basata su turnazioni')
    ], default='Oraria', validators=[DataRequired()])
    active = BooleanField('Attiva', default=True)
    submit = SubmitField('Salva Sede')
    
    def __init__(self, original_name=None, *args, **kwargs):
        super(SedeForm, self).__init__(*args, **kwargs)
        self.original_name = original_name
    
    def validate_name(self, name):
        """Valida che il nome della sede sia unico"""
        if name.data != self.original_name:
            from models import Sede as SedeModel
            sede = SedeModel.query.filter_by(name=name.data).first()
            if sede:
                raise ValidationError('Nome sede già esistente. Scegli un altro nome.')


class WorkScheduleForm(FlaskForm):
    """Form per gestire gli orari di lavoro"""
    sede = SelectField('Sede (opzionale)', coerce=coerce_nullable_int, validators=[Optional()])
    name = StringField('Nome Orario', validators=[DataRequired(), Length(max=100)])
    
    # Range orari di entrata
    start_time_min = TimeField('Entrata Min', validators=[DataRequired()])
    start_time_max = TimeField('Entrata Max', validators=[DataRequired()])
    
    # Range orari di uscita  
    end_time_min = TimeField('Uscita Min', validators=[DataRequired()])
    end_time_max = TimeField('Uscita Max', validators=[DataRequired()])
    
    # Preset e selezione giorni della settimana
    days_preset = SelectField('Preset Giorni', choices=[
        ('workdays', 'Lunedì-Venerdì'),
        ('weekend', 'Sabato-Domenica'),
        ('all_week', 'Tutti i giorni'),
        ('custom', 'Personalizzato')
    ], default='workdays')
    
    days_of_week = SelectMultipleField('Giorni della Settimana', choices=[
        (0, 'Lunedì'),
        (1, 'Martedì'),
        (2, 'Mercoledì'),
        (3, 'Giovedì'),
        (4, 'Venerdì'),
        (5, 'Sabato'),
        (6, 'Domenica')
    ], coerce=int, default=[0, 1, 2, 3, 4])
    
    description = TextAreaField('Descrizione', validators=[Length(max=500)])
    active = BooleanField('Attivo', default=True)
    submit = SubmitField('Salva Orario')
    
    def __init__(self, *args, **kwargs):
        super(WorkScheduleForm, self).__init__(*args, **kwargs)
        # Popola le scelte delle sedi attive, con opzione vuota per orari globali
        try:
            from models import Sede as SedeModel
            from utils_tenant import filter_by_company
            sedi_attive = filter_by_company(SedeModel.query).filter_by(active=True).all()
            self.sede.choices = [('', '-- Orario Globale (nessuna sede) --')] + [(sede.id, sede.name) for sede in sedi_attive]
        except:
            self.sede.choices = [('', '-- Orario Globale (nessuna sede) --')]
    
    def validate_days_of_week(self, days_of_week):
        """Valida che almeno un giorno sia selezionato"""
        if not days_of_week.data:
            raise ValidationError('Seleziona almeno un giorno della settimana.')
    
    def get_days_from_preset(self, preset):
        """Restituisce i giorni corrispondenti al preset selezionato"""
        presets = {
            'workdays': [0, 1, 2, 3, 4],  # Lun-Ven
            'weekend': [5, 6],            # Sab-Dom
            'all_week': [0, 1, 2, 3, 4, 5, 6],  # Tutti
            'custom': []                  # Da definire manualmente
        }
        return presets.get(preset, [0, 1, 2, 3, 4])
    
    def validate_start_time_max(self, start_time_max):
        """Valida che l'orario massimo di entrata sia >= al minimo"""
        if self.start_time_min.data and start_time_max.data:
            if start_time_max.data < self.start_time_min.data:
                raise ValidationError('L\'orario massimo di entrata deve essere maggiore o uguale al minimo.')
    
    def validate_end_time_max(self, end_time_max):
        """Valida che l'orario massimo di uscita sia >= al minimo"""
        if self.end_time_min.data and end_time_max.data:
            if end_time_max.data < self.end_time_min.data:
                raise ValidationError('L\'orario massimo di uscita deve essere maggiore o uguale al minimo.')
    
    def validate_end_time_min(self, end_time_min):
        """Valida che l'orario minimo di uscita sia successivo all'entrata"""
        if self.start_time_max.data and end_time_min.data:
            if end_time_min.data <= self.start_time_max.data:
                # Solo alza warning se non attraversa mezzanotte
                if not (end_time_min.data.hour < 12 and self.start_time_max.data.hour > 12):
                    raise ValidationError('L\'orario di uscita deve essere successivo all\'entrata.')
    
    def validate_name(self, name):
        """Valida che il nome dell'orario sia unico per la sede"""
        if self.sede.data and name.data:
            from models import WorkSchedule as WorkScheduleModel
            existing = WorkScheduleModel.query.filter_by(
                sede_id=self.sede.data, 
                name=name.data
            ).first()
            if existing:
                raise ValidationError('Nome orario già esistente per questa sede. Scegli un altro nome.')


class RoleForm(FlaskForm):
    """Form per gestire i ruoli dinamici"""
    name = StringField('Nome Ruolo (Codice)', validators=[Length(max=50)])
    display_name = StringField('Nome Visualizzato', validators=[Length(max=100)])
    description = TextAreaField('Descrizione', validators=[Length(max=500)])
    
    # Permessi come checkboxes - Sistema completo di permessi granulari
    # Dashboard e sistema base
    can_access_dashboard = BooleanField('Accedere alla Dashboard', default=True)
    
    # Gestione ruoli
    can_manage_roles = BooleanField('Gestire Ruoli')
    can_view_roles = BooleanField('Visualizzare Ruoli')
    
    # Gestione utenti
    can_manage_users = BooleanField('Gestire Utenti')
    can_view_users = BooleanField('Visualizzare Utenti')
    
    # Gestione sedi
    can_manage_sedi = BooleanField('Gestire Sedi')
    can_view_sedi = BooleanField('Visualizzare Sedi')
    
    # Gestione orari/scheduli
    can_manage_schedules = BooleanField('Gestire Orari')
    can_view_schedules = BooleanField('Visualizzare Orari')
    
    # Gestione turni
    can_manage_shifts = BooleanField('Gestione Coperture')
    can_view_shifts = BooleanField('Visualizza Coperture')
    
    # Reperibilità
    can_manage_reperibilita = BooleanField('Gestire Reperibilità')
    can_view_reperibilita = BooleanField('Visualizzare Tutte le Reperibilità')
    can_view_my_reperibilita = BooleanField('Visualizzare Le Mie Reperibilità')
    can_manage_coverage = BooleanField('Gestire Coperture Reperibilità')
    can_view_coverage = BooleanField('Visualizzare Coperture Reperibilità')
    
    # Gestione presenze
    can_manage_attendance = BooleanField('Gestire Presenze')
    can_view_attendance = BooleanField('Visualizzare Tutte le Presenze')
    can_view_my_attendance = BooleanField('Visualizzare Le Mie Presenze')
    can_access_attendance = BooleanField('Accedere alle Presenze', default=True)
    can_view_sede_attendance = BooleanField('Visualizzare Presenze Sede')
    
    # Gestione ferie/permessi
    can_manage_leave = BooleanField('Gestire Ferie/Permessi')
    can_approve_leave = BooleanField('Approvare Ferie/Permessi')
    can_request_leave = BooleanField('Richiedere Ferie/Permessi')
    can_view_leave = BooleanField('Visualizzare Tutte le Ferie/Permessi')
    can_view_my_leave = BooleanField('Visualizzare Le Mie Ferie/Permessi')
    
    # Gestione interventi
    can_manage_interventions = BooleanField('Gestire Interventi')
    can_view_interventions = BooleanField('Visualizzare Tutti gli Interventi')
    can_view_my_interventions = BooleanField('Visualizzare I Miei Interventi')
    
    # Gestione festività
    can_manage_holidays = BooleanField('Gestire Festività')
    can_view_holidays = BooleanField('Visualizzare Festività')
    
    # HR - Human Resources
    can_manage_hr_data = BooleanField('Gestire Dati HR')
    can_view_hr_data = BooleanField('Visualizzare Tutti i Dati HR')
    can_view_my_hr_data = BooleanField('Visualizzare I Miei Dati HR')
    
    # Gestione QR
    can_manage_qr = BooleanField('Gestire QR')
    can_view_qr = BooleanField('Visualizzare QR')
    
    # Report e statistiche
    can_view_reports = BooleanField('Visualizzare Report')
    can_manage_reports = BooleanField('Gestire Report')
    can_view_statistics = BooleanField('Visualizzare Statistiche')
    
    # Messaggi
    can_send_messages = BooleanField('Inviare Messaggi')
    can_view_messages = BooleanField('Visualizzare Messaggi')
    
    # Note spese
    can_manage_expense_reports = BooleanField('Gestire Note Spese')
    can_view_expense_reports = BooleanField('Visualizzare Note Spese')
    can_view_my_expense_reports = BooleanField('Visualizzare Le Mie Note Spese')
    can_approve_expense_reports = BooleanField('Approvare Note Spese')
    can_create_expense_reports = BooleanField('Creare Note Spese')
    
    # Dashboard Widget Permissions
    can_view_team_stats_widget = BooleanField('Widget Statistiche Team')
    can_view_my_attendance_widget = BooleanField('Widget Le Mie Presenze')
    can_view_team_management_widget = BooleanField('Widget Gestione Team')
    can_view_leave_requests_widget = BooleanField('Widget Ferie/Permessi')
    can_view_my_leave_requests_widget = BooleanField('Widget Le Mie Richieste')
    can_view_daily_attendance_widget = BooleanField('Widget Presenze per Sede')
    can_view_shifts_coverage_widget = BooleanField('Widget Coperture Turni')
    can_view_my_shifts_widget = BooleanField('Widget I Miei Turni')
    can_view_reperibilita_widget = BooleanField('Widget Reperibilità')
    can_view_my_reperibilita_widget = BooleanField('Widget Le Mie Reperibilità')
    can_view_expense_reports_widget = BooleanField('Widget Note Spese')
    
    # Gestione Straordinari
    can_manage_overtime_requests = BooleanField('Gestire Richieste Straordinari')
    can_approve_overtime_requests = BooleanField('Approvare Richieste Straordinari')
    can_create_overtime_requests = BooleanField('Creare Richieste Straordinari')
    can_view_overtime_requests = BooleanField('Visualizzare Richieste Straordinari')
    can_view_my_overtime_requests = BooleanField('Visualizzare Le Mie Richieste')
    can_manage_overtime_types = BooleanField('Gestire Tipologie Straordinari')
    
    # Widget Straordinari
    can_view_overtime_widget = BooleanField('Widget Straordinari')
    can_view_my_overtime_widget = BooleanField('Widget I Miei Straordinari')
    
    # Gestione Rimborsi Chilometrici
    can_create_mileage_requests = BooleanField('Creare Richieste Rimborso Km')
    can_view_mileage_requests = BooleanField('Visualizzare Richieste Rimborso Km')
    can_approve_mileage_requests = BooleanField('Approvare Richieste Rimborso Km')
    can_manage_mileage_requests = BooleanField('Gestire Richieste Rimborso Km')
    can_view_my_mileage_requests = BooleanField('Visualizzare Le Mie Richieste Rimborso Km')
    
    # Widget Rimborsi Chilometrici
    can_view_mileage_widget = BooleanField('Widget Rimborsi Chilometrici')
    can_view_my_mileage_widget = BooleanField('Widget I Miei Rimborsi')
    
    # Widget Banca Ore
    can_view_banca_ore_widget = BooleanField('Widget Banca Ore')
    can_view_my_banca_ore_widget = BooleanField('Widget La Mia Banca Ore')
    
    # Gestione Tabelle ACI
    can_manage_aci_tables = BooleanField('Gestire Tabelle ACI')
    can_view_aci_tables = BooleanField('Visualizzare Tabelle ACI')
    
    # CIRCLE - Social Intranet Permissions
    can_access_hubly = BooleanField('Accedere a CIRCLE')
    can_create_posts = BooleanField('Creare Post/News')
    can_edit_posts = BooleanField('Modificare Post/News')
    can_delete_posts = BooleanField('Eliminare Post/News')
    can_manage_groups = BooleanField('Gestire Gruppi')
    can_create_groups = BooleanField('Creare Gruppi')
    can_join_groups = BooleanField('Unirsi ai Gruppi')
    can_create_polls = BooleanField('Creare Sondaggi')
    can_vote_polls = BooleanField('Votare Sondaggi')
    can_manage_documents = BooleanField('Gestire Documenti')
    can_view_documents = BooleanField('Visualizzare Documenti')
    can_upload_documents = BooleanField('Caricare Documenti')
    can_manage_calendar = BooleanField('Gestire Calendario')
    can_view_calendar = BooleanField('Visualizzare Calendario')
    can_create_events = BooleanField('Creare Eventi')
    can_manage_tools = BooleanField('Gestire Strumenti Esterni')
    can_view_tools = BooleanField('Visualizzare Strumenti')
    can_comment_posts = BooleanField('Commentare Post')
    can_like_posts = BooleanField('Mettere Like ai Post')
    
    active = BooleanField('Attivo', default=True)
    submit = SubmitField('Salva Ruolo')
    
    def __init__(self, original_name=None, widget_only=False, protected_permissions=None, *args, **kwargs):
        super(RoleForm, self).__init__(*args, **kwargs)
        self.original_name = original_name
        self.widget_only = widget_only
        self.protected_permissions = protected_permissions or []
        
        # Se è widget_only, rimuovi i validator richiesti
        if not widget_only:
            self.name.validators = [DataRequired(), Length(max=50)]
            self.display_name.validators = [DataRequired(), Length(max=100)]
    
    def validate_name(self, name):
        """Valida che il nome del ruolo sia unico"""
        # Salta la validazione se è in modalità widget_only
        if self.widget_only:
            return
            
        if name.data != self.original_name:
            from utils_tenant import filter_by_company
            role = filter_by_company(UserRole.query).filter_by(name=name.data).first()
            if role:
                raise ValidationError('Nome ruolo già esistente. Scegli un altro nome.')
    
    def get_permissions_dict(self):
        """Converte i permessi del form in un dizionario"""
        return {
            # Dashboard e sistema base
            'can_access_dashboard': self.can_access_dashboard.data,
            
            # Gestione ruoli
            'can_manage_roles': self.can_manage_roles.data,
            'can_view_roles': self.can_view_roles.data,
            
            # Gestione utenti
            'can_manage_users': self.can_manage_users.data,
            'can_view_users': self.can_view_users.data,
            
            # Gestione sedi
            'can_manage_sedi': self.can_manage_sedi.data,
            'can_view_sedi': self.can_view_sedi.data,
            
            # Gestione orari/scheduli
            'can_manage_schedules': self.can_manage_schedules.data,
            'can_view_schedules': self.can_view_schedules.data,
            
            # Gestione turni
            'can_manage_shifts': self.can_manage_shifts.data,
            'can_view_shifts': self.can_view_shifts.data,
            
            # Reperibilità
            'can_manage_reperibilita': self.can_manage_reperibilita.data,
            'can_view_reperibilita': self.can_view_reperibilita.data,
            'can_view_my_reperibilita': self.can_view_my_reperibilita.data,
            'can_manage_coverage': self.can_manage_coverage.data,
            'can_view_coverage': self.can_view_coverage.data,
            
            # Gestione presenze
            'can_manage_attendance': self.can_manage_attendance.data,
            'can_view_attendance': self.can_view_attendance.data,
            'can_view_my_attendance': self.can_view_my_attendance.data,
            'can_access_attendance': self.can_access_attendance.data,
            'can_view_sede_attendance': self.can_view_sede_attendance.data,
            
            # Gestione ferie/permessi
            'can_manage_leave': self.can_manage_leave.data,
            'can_approve_leave': self.can_approve_leave.data,
            'can_request_leave': self.can_request_leave.data,
            'can_view_leave': self.can_view_leave.data,
            'can_view_my_leave': self.can_view_my_leave.data,
            
            # Gestione interventi
            'can_manage_interventions': self.can_manage_interventions.data,
            'can_view_interventions': self.can_view_interventions.data,
            'can_view_my_interventions': self.can_view_my_interventions.data,
            
            # Gestione festività
            'can_manage_holidays': self.can_manage_holidays.data,
            'can_view_holidays': self.can_view_holidays.data,
            
            # HR - Human Resources
            'can_manage_hr_data': self.can_manage_hr_data.data,
            'can_view_hr_data': self.can_view_hr_data.data,
            'can_view_my_hr_data': self.can_view_my_hr_data.data,
            
            # Gestione QR
            'can_manage_qr': self.can_manage_qr.data,
            'can_view_qr': self.can_view_qr.data,
            
            # Report e statistiche
            'can_view_reports': self.can_view_reports.data,
            'can_manage_reports': self.can_manage_reports.data,
            'can_view_statistics': self.can_view_statistics.data,
            
            # Messaggi
            'can_send_messages': self.can_send_messages.data,
            'can_view_messages': self.can_view_messages.data,
            
            # Note spese
            'can_manage_expense_reports': self.can_manage_expense_reports.data,
            'can_view_expense_reports': self.can_view_expense_reports.data,
            'can_view_my_expense_reports': self.can_view_my_expense_reports.data,
            'can_approve_expense_reports': self.can_approve_expense_reports.data,
            'can_create_expense_reports': self.can_create_expense_reports.data,
            
            # Dashboard Widget Permissions
            'can_view_team_stats_widget': self.can_view_team_stats_widget.data,
            'can_view_my_attendance_widget': self.can_view_my_attendance_widget.data,
            'can_view_team_management_widget': self.can_view_team_management_widget.data,
            'can_view_leave_requests_widget': self.can_view_leave_requests_widget.data,
            'can_view_my_leave_requests_widget': self.can_view_my_leave_requests_widget.data,
            'can_view_daily_attendance_widget': self.can_view_daily_attendance_widget.data,
            'can_view_shifts_coverage_widget': self.can_view_shifts_coverage_widget.data,
            'can_view_my_shifts_widget': self.can_view_my_shifts_widget.data,
            'can_view_reperibilita_widget': self.can_view_reperibilita_widget.data,
            'can_view_my_reperibilita_widget': self.can_view_my_reperibilita_widget.data,
            'can_view_expense_reports_widget': self.can_view_expense_reports_widget.data,
            
            # Widget Straordinari  
            # Gestione Straordinari
            'can_manage_overtime_requests': self.can_manage_overtime_requests.data,
            'can_approve_overtime_requests': self.can_approve_overtime_requests.data,
            'can_create_overtime_requests': self.can_create_overtime_requests.data,
            'can_view_overtime_requests': self.can_view_overtime_requests.data,
            'can_view_my_overtime_requests': self.can_view_my_overtime_requests.data,
            'can_manage_overtime_types': self.can_manage_overtime_types.data,
            
            'can_view_overtime_widget': self.can_view_overtime_widget.data,
            'can_view_my_overtime_widget': self.can_view_my_overtime_widget.data,
            
            # Rimborsi chilometrici
            'can_create_mileage_requests': self.can_create_mileage_requests.data,
            'can_view_mileage_requests': self.can_view_mileage_requests.data,
            'can_approve_mileage_requests': self.can_approve_mileage_requests.data,
            'can_manage_mileage_requests': self.can_manage_mileage_requests.data,
            'can_view_my_mileage_requests': self.can_view_my_mileage_requests.data,
            'can_view_mileage_widget': self.can_view_mileage_widget.data,
            'can_view_my_mileage_widget': self.can_view_my_mileage_widget.data,
            
            # Widget Banca Ore
            'can_view_banca_ore_widget': self.can_view_banca_ore_widget.data,
            'can_view_my_banca_ore_widget': self.can_view_my_banca_ore_widget.data,
            
            # Gestione Tabelle ACI
            'can_manage_aci_tables': self.can_manage_aci_tables.data,
            'can_view_aci_tables': self.can_view_aci_tables.data,
            
            # CIRCLE - Social Intranet
            'can_access_hubly': self.can_access_hubly.data,
            'can_create_posts': self.can_create_posts.data,
            'can_edit_posts': self.can_edit_posts.data,
            'can_delete_posts': self.can_delete_posts.data,
            'can_manage_groups': self.can_manage_groups.data,
            'can_create_groups': self.can_create_groups.data,
            'can_join_groups': self.can_join_groups.data,
            'can_create_polls': self.can_create_polls.data,
            'can_vote_polls': self.can_vote_polls.data,
            'can_manage_documents': self.can_manage_documents.data,
            'can_view_documents': self.can_view_documents.data,
            'can_upload_documents': self.can_upload_documents.data,
            'can_manage_calendar': self.can_manage_calendar.data,
            'can_view_calendar': self.can_view_calendar.data,
            'can_create_events': self.can_create_events.data,
            'can_manage_tools': self.can_manage_tools.data,
            'can_view_tools': self.can_view_tools.data,
            'can_comment_posts': self.can_comment_posts.data,
            'can_like_posts': self.can_like_posts.data
        }
    
    def populate_permissions(self, permissions_dict):
        """Popola i campi permessi dal dizionario"""
        # Dashboard e sistema base
        self.can_access_dashboard.data = permissions_dict.get('can_access_dashboard', True)
        
        # Gestione ruoli
        self.can_manage_roles.data = permissions_dict.get('can_manage_roles', False)
        self.can_view_roles.data = permissions_dict.get('can_view_roles', False)
        
        # Gestione utenti
        self.can_manage_users.data = permissions_dict.get('can_manage_users', False)
        self.can_view_users.data = permissions_dict.get('can_view_users', False)
        
        # Gestione sedi
        self.can_manage_sedi.data = permissions_dict.get('can_manage_sedi', False)
        self.can_view_sedi.data = permissions_dict.get('can_view_sedi', False)
        
        # Gestione orari/scheduli
        self.can_manage_schedules.data = permissions_dict.get('can_manage_schedules', False)
        self.can_view_schedules.data = permissions_dict.get('can_view_schedules', False)
        
        # Gestione turni
        self.can_manage_shifts.data = permissions_dict.get('can_manage_shifts', False)
        self.can_view_shifts.data = permissions_dict.get('can_view_shifts', False)
        
        # Reperibilità
        self.can_manage_reperibilita.data = permissions_dict.get('can_manage_reperibilita', False)
        self.can_view_reperibilita.data = permissions_dict.get('can_view_reperibilita', False)
        self.can_view_my_reperibilita.data = permissions_dict.get('can_view_my_reperibilita', False)
        self.can_manage_coverage.data = permissions_dict.get('can_manage_coverage', False)
        self.can_view_coverage.data = permissions_dict.get('can_view_coverage', False)
        
        # Gestione presenze
        self.can_manage_attendance.data = permissions_dict.get('can_manage_attendance', False)
        self.can_view_attendance.data = permissions_dict.get('can_view_attendance', False)
        self.can_view_my_attendance.data = permissions_dict.get('can_view_my_attendance', False)
        self.can_access_attendance.data = permissions_dict.get('can_access_attendance', True)
        self.can_view_sede_attendance.data = permissions_dict.get('can_view_sede_attendance', False)
        
        # Gestione ferie/permessi
        self.can_manage_leave.data = permissions_dict.get('can_manage_leave', False)
        self.can_approve_leave.data = permissions_dict.get('can_approve_leave', False)
        self.can_request_leave.data = permissions_dict.get('can_request_leave', False)
        self.can_view_leave.data = permissions_dict.get('can_view_leave', False)
        self.can_view_my_leave.data = permissions_dict.get('can_view_my_leave', False)
        
        # Gestione interventi
        self.can_manage_interventions.data = permissions_dict.get('can_manage_interventions', False)
        self.can_view_interventions.data = permissions_dict.get('can_view_interventions', False)
        self.can_view_my_interventions.data = permissions_dict.get('can_view_my_interventions', False)
        
        # Gestione festività
        self.can_manage_holidays.data = permissions_dict.get('can_manage_holidays', False)
        self.can_view_holidays.data = permissions_dict.get('can_view_holidays', False)
        
        # HR - Human Resources
        self.can_manage_hr_data.data = permissions_dict.get('can_manage_hr_data', False)
        self.can_view_hr_data.data = permissions_dict.get('can_view_hr_data', False)
        self.can_view_my_hr_data.data = permissions_dict.get('can_view_my_hr_data', False)
        
        # Gestione QR
        self.can_manage_qr.data = permissions_dict.get('can_manage_qr', False)
        self.can_view_qr.data = permissions_dict.get('can_view_qr', False)
        
        # Report e statistiche
        self.can_view_reports.data = permissions_dict.get('can_view_reports', False)
        self.can_manage_reports.data = permissions_dict.get('can_manage_reports', False)
        self.can_view_statistics.data = permissions_dict.get('can_view_statistics', False)
        
        # Messaggi
        self.can_send_messages.data = permissions_dict.get('can_send_messages', False)
        self.can_view_messages.data = permissions_dict.get('can_view_messages', False)
        
        # Note spese
        self.can_manage_expense_reports.data = permissions_dict.get('can_manage_expense_reports', False)
        self.can_view_expense_reports.data = permissions_dict.get('can_view_expense_reports', False)
        self.can_view_my_expense_reports.data = permissions_dict.get('can_view_my_expense_reports', False)
        self.can_approve_expense_reports.data = permissions_dict.get('can_approve_expense_reports', False)
        self.can_create_expense_reports.data = permissions_dict.get('can_create_expense_reports', False)
        
        # Dashboard Widget Permissions
        self.can_view_team_stats_widget.data = permissions_dict.get('can_view_team_stats_widget', False)
        self.can_view_my_attendance_widget.data = permissions_dict.get('can_view_my_attendance_widget', False)
        self.can_view_team_management_widget.data = permissions_dict.get('can_view_team_management_widget', False)
        self.can_view_leave_requests_widget.data = permissions_dict.get('can_view_leave_requests_widget', False)
        self.can_view_my_leave_requests_widget.data = permissions_dict.get('can_view_my_leave_requests_widget', False)
        self.can_view_daily_attendance_widget.data = permissions_dict.get('can_view_daily_attendance_widget', False)
        self.can_view_shifts_coverage_widget.data = permissions_dict.get('can_view_shifts_coverage_widget', False)
        self.can_view_my_shifts_widget.data = permissions_dict.get('can_view_my_shifts_widget', False)
        self.can_view_reperibilita_widget.data = permissions_dict.get('can_view_reperibilita_widget', False)
        self.can_view_my_reperibilita_widget.data = permissions_dict.get('can_view_my_reperibilita_widget', False)
        self.can_view_expense_reports_widget.data = permissions_dict.get('can_view_expense_reports_widget', False)
        
        # Widget Straordinari
        # Gestione Straordinari
        self.can_manage_overtime_requests.data = permissions_dict.get('can_manage_overtime_requests', False)
        self.can_approve_overtime_requests.data = permissions_dict.get('can_approve_overtime_requests', False)
        self.can_create_overtime_requests.data = permissions_dict.get('can_create_overtime_requests', False)
        self.can_view_overtime_requests.data = permissions_dict.get('can_view_overtime_requests', False)
        self.can_view_my_overtime_requests.data = permissions_dict.get('can_view_my_overtime_requests', False)
        self.can_manage_overtime_types.data = permissions_dict.get('can_manage_overtime_types', False)
        
        self.can_view_overtime_widget.data = permissions_dict.get('can_view_overtime_widget', False)
        self.can_view_my_overtime_widget.data = permissions_dict.get('can_view_my_overtime_widget', False)
        
        # Rimborsi chilometrici
        self.can_create_mileage_requests.data = permissions_dict.get('can_create_mileage_requests', False)
        self.can_view_mileage_requests.data = permissions_dict.get('can_view_mileage_requests', False)
        self.can_approve_mileage_requests.data = permissions_dict.get('can_approve_mileage_requests', False)
        self.can_manage_mileage_requests.data = permissions_dict.get('can_manage_mileage_requests', False)
        self.can_view_my_mileage_requests.data = permissions_dict.get('can_view_my_mileage_requests', False)
        self.can_view_mileage_widget.data = permissions_dict.get('can_view_mileage_widget', False)
        self.can_view_my_mileage_widget.data = permissions_dict.get('can_view_my_mileage_widget', False)
        
        # Widget Banca Ore
        self.can_view_banca_ore_widget.data = permissions_dict.get('can_view_banca_ore_widget', False)
        self.can_view_my_banca_ore_widget.data = permissions_dict.get('can_view_my_banca_ore_widget', False)
        
        # Gestione Tabelle ACI
        self.can_manage_aci_tables.data = permissions_dict.get('can_manage_aci_tables', False)
        self.can_view_aci_tables.data = permissions_dict.get('can_view_aci_tables', False)
        
        # CIRCLE - Social Intranet
        self.can_access_hubly.data = permissions_dict.get('can_access_hubly', False)
        self.can_create_posts.data = permissions_dict.get('can_create_posts', False)
        self.can_edit_posts.data = permissions_dict.get('can_edit_posts', False)
        self.can_delete_posts.data = permissions_dict.get('can_delete_posts', False)
        self.can_manage_groups.data = permissions_dict.get('can_manage_groups', False)
        self.can_create_groups.data = permissions_dict.get('can_create_groups', False)
        self.can_join_groups.data = permissions_dict.get('can_join_groups', False)
        self.can_create_polls.data = permissions_dict.get('can_create_polls', False)
        self.can_vote_polls.data = permissions_dict.get('can_vote_polls', False)
        self.can_manage_documents.data = permissions_dict.get('can_manage_documents', False)
        self.can_view_documents.data = permissions_dict.get('can_view_documents', False)
        self.can_upload_documents.data = permissions_dict.get('can_upload_documents', False)
        self.can_manage_calendar.data = permissions_dict.get('can_manage_calendar', False)
        self.can_view_calendar.data = permissions_dict.get('can_view_calendar', False)
        self.can_create_events.data = permissions_dict.get('can_create_events', False)
        self.can_manage_tools.data = permissions_dict.get('can_manage_tools', False)
        self.can_view_tools.data = permissions_dict.get('can_view_tools', False)
        self.can_comment_posts.data = permissions_dict.get('can_comment_posts', False)
        self.can_like_posts.data = permissions_dict.get('can_like_posts', False)


# Form del pacchetto presidio integrati
class PresidioCoverageTemplateForm(FlaskForm):
    """Form per creare/modificare il template di copertura presidio"""
    name = StringField('Nome Template', validators=[
        DataRequired(message='Il nome del template è obbligatorio'), 
        Length(max=100, message='Il nome non può superare 100 caratteri')
    ])
    
    sede_id = SelectField('Sede Turni', coerce=lambda x: int(x) if x and x != '' and x != 'None' else None, 
                         validators=[DataRequired(message='Seleziona una sede abilitata per i turni')])
    
    start_date = DateField('Data Inizio Validità', validators=[
        DataRequired(message='La data di inizio validità è obbligatoria')
    ])
    
    end_date = DateField('Data Fine Validità', validators=[
        DataRequired(message='La data di fine validità è obbligatoria')
    ])
    
    description = TextAreaField('Descrizione', validators=[
        Length(max=200, message='La descrizione non può superare 200 caratteri')
    ], render_kw={'rows': 3, 'placeholder': 'Descrizione opzionale del template'})
    
    submit = SubmitField('Salva Template')
    
    def __init__(self, *args, **kwargs):
        super(PresidioCoverageTemplateForm, self).__init__(*args, **kwargs)
        
        # Popola solo le sedi abilitate per i turni
        from models import Sede
        sedi_turni = Sede.query.filter_by(active=True, tipologia='Turni').order_by(Sede.name).all()
        self.sede_id.choices = [('', 'Seleziona una sede...')] + [(s.id, s.name) for s in sedi_turni]

    def validate_end_date(self, end_date):
        """Verifica che la data di fine sia successiva alla data di inizio"""
        if end_date.data and self.start_date.data:
            if end_date.data < self.start_date.data:
                raise ValidationError('La data di fine validità deve essere successiva alla data di inizio')
            
            # Verifica che non sia troppo nel passato
            from datetime import date
            if end_date.data < date.today():
                raise ValidationError('La data di fine validità non può essere nel passato')

    def validate_start_date(self, start_date):
        """Verifica che la data di inizio non sia troppo nel passato"""
        if start_date.data:
            from datetime import date, timedelta
            # Permetti massimo 30 giorni nel passato
            min_date = date.today() - timedelta(days=30)
            if start_date.data < min_date:
                raise ValidationError('La data di inizio non può essere più di 30 giorni nel passato')

class PresidioCoverageForm(FlaskForm):
    """Form per aggiungere/modificare singole coperture presidio"""
    days_of_week = SelectMultipleField('Giorni della Settimana', choices=[
        (0, 'Lunedì'),
        (1, 'Martedì'),
        (2, 'Mercoledì'),
        (3, 'Giovedì'),
        (4, 'Venerdì'),
        (5, 'Sabato'),
        (6, 'Domenica')
    ], coerce=int, validators=[
        DataRequired(message='Seleziona almeno un giorno della settimana')
    ], render_kw={
        'class': 'form-select', 
        'size': '7', 
        'multiple': True,
        'data-placeholder': 'Seleziona uno o più giorni'
    })
    
    start_time = TimeField('Ora Inizio', validators=[
        DataRequired(message='L\'ora di inizio è obbligatoria')
    ])
    
    end_time = TimeField('Ora Fine', validators=[
        DataRequired(message='L\'ora di fine è obbligatoria')
    ])
    
    required_roles = SelectMultipleField('Ruoli Richiesti', choices=[
        ('Amministratore', 'Amministratore'),
        ('Responsabile', 'Responsabile'),
        ('Supervisore', 'Supervisore'),
        ('Operatore', 'Operatore'),
        ('Ospite', 'Ospite')
    ], validators=[
        DataRequired(message='Seleziona almeno un ruolo richiesto')
    ], render_kw={
        'class': 'form-select',
        'multiple': True,
        'data-placeholder': 'Seleziona uno o più ruoli'
    })
    
    role_count = IntegerField('Numero Persone per Ruolo', validators=[
        DataRequired(message='Il numero di persone è obbligatorio'),
        NumberRange(min=1, max=10, message='Il numero deve essere tra 1 e 10')
    ], default=1, render_kw={
        'class': 'form-control',
        'min': 1,
        'max': 10
    })
    
    # Campi per la pausa - stringhe per permettere valori vuoti
    break_start = StringField('Ora Inizio Pausa', render_kw={
        'type': 'time', 
        'placeholder': 'Opzionale',
        'class': 'form-control'
    })
    
    break_end = StringField('Ora Fine Pausa', render_kw={
        'type': 'time', 
        'placeholder': 'Opzionale',
        'class': 'form-control'
    })
    
    description = StringField('Descrizione', validators=[
        Length(max=200, message='La descrizione non può superare 200 caratteri')
    ], render_kw={
        'class': 'form-control',
        'placeholder': 'Descrizione opzionale della copertura'
    })
    
    active = BooleanField('Attiva', default=True)
    
    # Pulsanti di azione
    submit = SubmitField('Salva Copertura')

    def validate_end_time(self, end_time):
        """Verifica che l'ora di fine sia successiva all'ora di inizio"""
        if end_time.data and self.start_time.data:
            if end_time.data <= self.start_time.data:
                raise ValidationError('L\'ora di fine deve essere successiva all\'ora di inizio')
            
            # Verifica che non sia più di 24 ore (turni molto lunghi)
            from datetime import datetime, timedelta
            start_dt = datetime.combine(datetime.today(), self.start_time.data)
            end_dt = datetime.combine(datetime.today(), end_time.data)
            
            # Se end_time è prima di start_time, assume sia il giorno dopo
            if end_dt <= start_dt:
                end_dt += timedelta(days=1)
            
            duration = (end_dt - start_dt).total_seconds() / 3600
            if duration > 24:  # Massimo 24 ore consecutive (copertura completa giornaliera)
                raise ValidationError('La copertura non può durare più di 24 ore consecutive')

class PresidioCoverageSearchForm(FlaskForm):
    """Form per ricerca e filtri delle coperture presidio"""
    template_name = StringField('Nome Template', render_kw={
        'placeholder': 'Cerca per nome template',
        'class': 'form-control'
    })
    
    date_from = DateField('Data Da', render_kw={
        'class': 'form-control'
    })
    
    date_to = DateField('Data A', render_kw={
        'class': 'form-control'
    })
    
    day_of_week = SelectField('Giorno Settimana', choices=[
        ('', 'Tutti i giorni'),
        (0, 'Lunedì'),
        (1, 'Martedì'),
        (2, 'Mercoledì'),
        (3, 'Giovedì'),
        (4, 'Venerdì'),
        (5, 'Sabato'),
        (6, 'Domenica')
    ], coerce=lambda x: int(x) if x else None, render_kw={
        'class': 'form-select'
    })
    
    active = SelectField('Stato', choices=[
        ('', 'Tutti'),
        ('true', 'Attivo'),
        ('false', 'Inattivo')
    ], render_kw={
        'class': 'form-select'
    })
    
    submit = SubmitField('Cerca')


# =============================================================================
# OVERTIME MANAGEMENT FORMS
# =============================================================================

class OvertimeTypeForm(FlaskForm):
    name = StringField('Nome Tipologia', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Descrizione')
    hourly_rate_multiplier = FloatField('Moltiplicatore Paga Oraria', validators=[DataRequired(), NumberRange(min=1.0, max=5.0)], default=1.5)
    active = BooleanField('Attiva', default=True)
    submit = SubmitField('Salva Tipologia')

class OvertimeRequestForm(FlaskForm):
    overtime_date = DateField('Data Straordinario', validators=[DataRequired()])
    start_time = TimeField('Ora Inizio', validators=[DataRequired()])
    end_time = TimeField('Ora Fine', validators=[DataRequired()])
    motivation = TextAreaField('Motivazione', validators=[DataRequired(), Length(max=500)])
    overtime_type_id = SelectField('Tipo Straordinario', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Invia Richiesta')
    
    def __init__(self, *args, **kwargs):
        super(OvertimeRequestForm, self).__init__(*args, **kwargs)
        
        # Popola le scelte dei tipi straordinario
        try:
            from models import OvertimeType
            active_types = OvertimeType.query.filter_by(active=True).all()
            self.overtime_type_id.choices = [(ot.id, ot.name) for ot in active_types]
            
            if not self.overtime_type_id.choices:
                self.overtime_type_id.choices = [(0, 'Nessuna tipologia disponibile')]
        except:
            self.overtime_type_id.choices = [(0, 'Errore nel caricamento tipologie')]
    
    def validate_end_time(self, field):
        if self.start_time.data and field.data:
            if field.data <= self.start_time.data:
                raise ValidationError('L\'ora di fine deve essere successiva all\'ora di inizio.')
    
    def validate_overtime_date(self, field):
        from datetime import date
        if field.data and field.data < date.today():
            raise ValidationError('Non è possibile richiedere straordinari per date passate.')

class ApproveOvertimeForm(FlaskForm):
    action = SelectField('Azione', choices=[
        ('approve', 'Approva'),
        ('reject', 'Rifiuta')
    ], validators=[DataRequired()])
    comment = TextAreaField('Commento')
    submit = SubmitField('Conferma')
    
    def validate_comment(self, field):
        if self.action.data == 'reject' and not field.data:
            raise ValidationError('Il commento è obbligatorio quando si rifiuta una richiesta.')


# Form per filtri straordinari
class OvertimeFilterForm(FlaskForm):
    """Form per filtrare le richieste straordinari"""
    status = SelectField('Stato', choices=[
        ('', 'Tutti'),
        ('pending', 'In Attesa'),
        ('approved', 'Approvate'),
        ('rejected', 'Rifiutate')
    ], default='')
    
    user_id = SelectField('Utente', coerce=lambda x: int(x) if x and x != '' and x != 'None' else None, choices=[])
    overtime_type_id = SelectField('Tipologia', coerce=lambda x: int(x) if x and x != '' and x != 'None' else None, choices=[])
    
    date_from = DateField('Da Data', format='%Y-%m-%d')
    date_to = DateField('A Data', format='%Y-%m-%d')
    
    submit = SubmitField('Filtra')
    
    def __init__(self, *args, **kwargs):
        super(OvertimeFilterForm, self).__init__(*args, **kwargs)
        
        # Popola gli utenti
        from models import User
        users = User.query.filter_by(active=True).order_by(User.username).all()
        self.user_id.choices = [('', 'Tutti gli utenti')] + [(u.id, f"{u.username} ({u.get_full_name()})") for u in users]
        
        # Popola le tipologie straordinari
        try:
            from models import OvertimeType
            overtime_types = OvertimeType.query.filter_by(active=True).order_by(OvertimeType.name).all()
            self.overtime_type_id.choices = [('', 'Tutte le tipologie')] + [(ot.id, ot.name) for ot in overtime_types]
        except:
            self.overtime_type_id.choices = [('', 'Tutte le tipologie')]


# =============================================================================
# MILEAGE REIMBURSEMENT FORMS
# =============================================================================

class MileageRequestForm(FlaskForm):
    """Form per creare/modificare richieste di rimborso chilometrico"""
    travel_date = DateField('Data Viaggio', validators=[DataRequired()])
    
    # Percorso multi-punto
    route_addresses = TextAreaField('Percorso (un indirizzo per riga)', 
                                  validators=[DataRequired()],
                                  render_kw={
                                      'placeholder': 'Esempio:\nVia Roma 32, Milano\nVia Milano 2, Roma\nVia Roma 32, Milano',
                                      'rows': 4
                                  })
    
    # Chilometraggio
    total_km = FloatField('Chilometri Totali', 
                         validators=[DataRequired(), NumberRange(min=0.1, max=9999.9)],
                         render_kw={'step': '0.1', 'placeholder': 'Es: 120.5'})
    
    is_km_manual = BooleanField('KM inseriti manualmente', default=False)
    
    # Veicolo (opzionale se l'utente ha già un veicolo assegnato)
    vehicle_id = SelectField('Veicolo ACI', coerce=lambda x: int(x) if x and x != '' else None, 
                           validators=[Optional()], validate_choice=False)
    vehicle_description = StringField('Descrizione Veicolo (se non in ACI)', 
                                    validators=[Optional(), Length(max=200)])
    
    # Motivazione
    purpose = TextAreaField('Scopo del Viaggio', 
                          validators=[DataRequired(), Length(max=500)],
                          render_kw={'rows': 3, 'placeholder': 'Descrivi brevemente il motivo del viaggio...'})
    
    notes = TextAreaField('Note Aggiuntive', 
                        validators=[Optional(), Length(max=500)],
                        render_kw={'rows': 2})
    
    submit = SubmitField('Invia Richiesta')
    
    def __init__(self, user=None, *args, **kwargs):
        super(MileageRequestForm, self).__init__(*args, **kwargs)
        self.user = user
        
        # Popola le scelte dei veicoli ACI
        try:
            from models import ACITable
            vehicles = ACITable.query.order_by(ACITable.marca, ACITable.modello).all()
            self.vehicle_id.choices = [('', 'Seleziona veicolo')] + [
                (v.id, f"{v.marca} {v.modello} (€{v.costo_km:.4f}/km)") 
                for v in vehicles
            ]
            
            # Se l'utente ha un veicolo assegnato, mostra solo quello
            if user and hasattr(user, 'aci_vehicle_id') and user.aci_vehicle_id:
                user_vehicle = ACITable.query.get(user.aci_vehicle_id)
                if user_vehicle:
                    # Mostra solo il veicolo assegnato all'utente
                    self.vehicle_id.choices = [
                        (user_vehicle.id, f"{user_vehicle.marca} {user_vehicle.modello} (€{user_vehicle.costo_km:.4f}/km) - VEICOLO ASSEGNATO")
                    ]
                    self.vehicle_id.data = user_vehicle.id
        except Exception as e:
            self.vehicle_id.choices = [('', 'Errore nel caricamento veicoli')]
    
    def validate_travel_date(self, field):
        """Valida che la data del viaggio non sia troppo nel futuro"""
        from datetime import date, timedelta
        if field.data:
            # Non permettere date più di 30 giorni nel futuro
            max_date = date.today() + timedelta(days=30)
            if field.data > max_date:
                raise ValidationError('La data del viaggio non può essere più di 30 giorni nel futuro.')
            
            # Non permettere date più di 365 giorni nel passato
            min_date = date.today() - timedelta(days=365)
            if field.data < min_date:
                raise ValidationError('La data del viaggio non può essere più di un anno nel passato.')
    
    def validate_route_addresses(self, field):
        """Valida che ci siano almeno 2 indirizzi"""
        if field.data:
            addresses = [addr.strip() for addr in field.data.split('\n') if addr.strip()]
            if len(addresses) < 2:
                raise ValidationError('Inserisci almeno 2 indirizzi (partenza e destinazione).')
            if len(addresses) > 10:
                raise ValidationError('Massimo 10 indirizzi consentiti.')
    
    def validate(self, extra_validators=None):
        """Validazione personalizzata del form"""
        if not super().validate(extra_validators):
            return False
        
        # Se non è selezionato un veicolo ACI, la descrizione del veicolo è obbligatoria
        if not self.vehicle_id.data and not self.vehicle_description.data:
            self.vehicle_description.errors.append('Seleziona un veicolo ACI oppure inserisci una descrizione del veicolo.')
            return False
        
        return True
    
    def get_route_addresses_list(self):
        """Restituisce la lista degli indirizzi dal campo textarea"""
        if self.route_addresses.data:
            return [addr.strip() for addr in self.route_addresses.data.split('\n') if addr.strip()]
        return []


class ApproveMileageForm(FlaskForm):
    """Form per approvare/rifiutare richieste di rimborso chilometrico"""
    action = SelectField('Azione', choices=[
        ('approve', 'Approva'),
        ('reject', 'Rifiuta')
    ], validators=[DataRequired()])
    comment = TextAreaField('Commento', render_kw={'rows': 3})
    submit = SubmitField('Conferma')
    
    def validate_comment(self, field):
        if self.action.data == 'reject' and not field.data:
            raise ValidationError('Il commento è obbligatorio quando si rifiuta una richiesta.')


class MileageFilterForm(FlaskForm):
    """Form per filtrare le richieste di rimborso chilometrico"""
    status = SelectField('Stato', choices=[
        ('', 'Tutti'),
        ('pending', 'In Attesa'),
        ('approved', 'Approvate'),
        ('rejected', 'Rifiutate')
    ], default='')
    
    user_id = SelectField('Utente', coerce=lambda x: int(x) if x and x != '' and x != 'None' else None, choices=[])
    
    date_from = DateField('Da Data', format='%Y-%m-%d')
    date_to = DateField('A Data', format='%Y-%m-%d')
    
    min_amount = FloatField('Importo Minimo (€)', render_kw={'step': '0.01', 'placeholder': '0.00'})
    max_amount = FloatField('Importo Massimo (€)', render_kw={'step': '0.01', 'placeholder': '999.99'})
    
    submit = SubmitField('Filtra')
    
    def __init__(self, current_user=None, *args, **kwargs):
        super(MileageFilterForm, self).__init__(*args, **kwargs)
        
        # Popola gli utenti in base ai permessi
        try:
            from models import User
            
            if current_user and current_user.all_sedi:
                # Utenti con accesso globale vedono tutti
                users = User.query.filter_by(active=True).order_by(User.username).all()
            elif current_user and current_user.sede_id:
                # Utenti con sede specifica vedono solo utenti della stessa sede
                users = User.query.filter_by(active=True, sede_id=current_user.sede_id).order_by(User.username).all()
            else:
                users = []
            
            # Semplifica la visualizzazione usando solo username per evitare errori
            self.user_id.choices = [('', 'Tutti gli utenti')] + [(u.id, u.username) for u in users]
        except Exception as e:
            # Fallback sicuro
            self.user_id.choices = [('', 'Tutti gli utenti')]


# Form per upload file Excel ACI
def validate_file_size(form, field):
    """Validatore per la dimensione del file (max 50MB)"""
    if field.data:
        # Reset file pointer per leggere la dimensione
        field.data.seek(0, 2)  # Vai alla fine del file
        size = field.data.tell()  # Ottieni dimensione in bytes
        field.data.seek(0)  # Torna all'inizio
        
        max_size = 50 * 1024 * 1024  # 50MB in bytes
        if size > max_size:
            raise ValidationError(f'File troppo grande: {size//1024//1024}MB. Massimo consentito: 50MB')

# =============================================================================
# ACI TABLES MANAGEMENT FORMS
# =============================================================================

class ACIUploadForm(FlaskForm):
    """Form per caricare file Excel delle tabelle ACI"""
    excel_file = FileField('File Excel ACI', validators=[
        DataRequired(),
        FileAllowed(['xlsx', 'xls'], 'Solo file Excel (.xlsx, .xls) sono permessi'),
        validate_file_size
    ])
    tipologia = StringField('Nome Tipologia', validators=[DataRequired(), Length(max=100)],
                          render_kw={'placeholder': 'Es: Plug-in IN 2025'})
    submit = SubmitField('Carica e Importa')


# Form per creazione/modifica manuale record ACI
class ACIRecordForm(FlaskForm):
    """Form per creare o modificare manualmente record ACI"""
    tipologia = StringField('Tipologia', validators=[DataRequired(), Length(max=100)],
                          render_kw={'placeholder': 'Lascia vuoto per usare nome file Excel'})
    marca = StringField('Marca', validators=[DataRequired(), Length(max=100)],
                       render_kw={'placeholder': 'Es: ALFA ROMEO'})
    modello = StringField('Modello', validators=[DataRequired(), Length(max=200)],
                         render_kw={'placeholder': 'Es: Giulia 2.0 Turbo 200 CV AT8'})
    costo_km = DecimalField('Costo per KM', validators=[DataRequired(), NumberRange(min=0)], 
                           places=4, rounding=None,
                           render_kw={'placeholder': '0.0000', 'step': '0.0001'})
    submit = SubmitField('Salva Record')


# Form per filtri tabelle ACI
class ACIFilterForm(FlaskForm):
    """Form per filtrare i record delle tabelle ACI"""
    tipologia = SelectField('Tipologia', choices=[('', 'Tutte le tipologie')])
    marca = SelectField('Marca', choices=[('', 'Tutte le marche')])
    modello = SelectField('Modello', choices=[('', 'Tutti i modelli')])
    submit = SubmitField('Filtra')
    
    def __init__(self, *args, **kwargs):
        super(ACIFilterForm, self).__init__(*args, **kwargs)
        
        # Popola dinamicamente le opzioni dai dati esistenti
        try:
            from models import ACITable
            from app import db
            
            # Tipologie uniche
            tipologie = db.session.query(ACITable.tipologia).distinct().order_by(ACITable.tipologia).all()
            self.tipologia.choices = [('', 'Tutte le tipologie')] + [(t.tipologia, t.tipologia) for t in tipologie]
            
            # Marche uniche
            marche = db.session.query(ACITable.marca).distinct().order_by(ACITable.marca).all()
            self.marca.choices = [('', 'Tutte le marche')] + [(m.marca, m.marca) for m in marche]
            
            # Modelli unici
            modelli = db.session.query(ACITable.modello).distinct().order_by(ACITable.modello).all()
            self.modello.choices = [('', 'Tutti i modelli')] + [(m.modello, m.modello) for m in modelli]
            
        except Exception as e:
            # Fallback se non ci sono dati o errore database
            self.tipologia.choices = [('', 'Tutte le tipologie')]
            self.marca.choices = [('', 'Tutte le marche')]


# =============================================================================
# EMAIL CONFIGURATION FORMS
# =============================================================================

class CompanyEmailSettingsForm(FlaskForm):
    """Form per configurare SMTP specifico dell'azienda"""
    mail_server = StringField('Server SMTP', validators=[DataRequired(), Length(max=255)],
                             render_kw={'placeholder': 'smtp.gmail.com'})
    mail_port = IntegerField('Porta SMTP', validators=[DataRequired(), NumberRange(min=1, max=65535)],
                            default=587, render_kw={'placeholder': '587'})
    mail_use_tls = BooleanField('Usa TLS', default=True)
    mail_use_ssl = BooleanField('Usa SSL', default=False)
    mail_username = StringField('Username SMTP', validators=[DataRequired(), Length(max=255)],
                               render_kw={'placeholder': 'noreply@tuaazienda.it'})
    mail_password = PasswordField('Password SMTP', validators=[DataRequired()],
                                 render_kw={'placeholder': 'Password del servizio SMTP'})
    mail_default_sender = StringField('Email Mittente', validators=[DataRequired(), Email(), Length(max=255)],
                                      render_kw={'placeholder': 'noreply@tuaazienda.it'})
    mail_reply_to = StringField('Email Reply-To (opzionale)', validators=[Optional(), Email(), Length(max=255)],
                               render_kw={'placeholder': 'support@tuaazienda.it'})
    submit = SubmitField('Salva Configurazione')


class TestEmailForm(FlaskForm):
    """Form per testare configurazione SMTP"""
    test_email = StringField('Email di Test', validators=[DataRequired(), Email()],
                            render_kw={'placeholder': 'tua.email@esempio.it'})
    submit = SubmitField('Invia Email di Test')


# =============================================================================
# PLATFORM NEWS FORMS
# =============================================================================

class PlatformNewsForm(FlaskForm):
    """Form per gestire novità e aggiornamenti della piattaforma"""
    title = StringField('Titolo', validators=[DataRequired(), Length(max=200)],
                       render_kw={'placeholder': 'Es: Nuovo Sistema Email Attivo'})
    description = TextAreaField('Descrizione', validators=[DataRequired()],
                               render_kw={'placeholder': 'Descrizione dettagliata della novità', 'rows': 4})
    icon_class = StringField('Classe Icona Font Awesome', validators=[DataRequired(), Length(max=100)],
                            default='fas fa-info-circle',
                            render_kw={'placeholder': 'Es: fas fa-check-circle'})
    icon_color = SelectField('Colore Icona', 
                            choices=[
                                ('text-primary', 'Blu (Primary)'),
                                ('text-success', 'Verde (Success)'),
                                ('text-info', 'Azzurro (Info)'),
                                ('text-warning', 'Giallo (Warning)'),
                                ('text-danger', 'Rosso (Danger)'),
                                ('text-secondary', 'Grigio (Secondary)')
                            ],
                            default='text-primary',
                            validators=[DataRequired()])
    order = IntegerField('Ordine di Visualizzazione', validators=[Optional()],
                        default=0,
                        render_kw={'placeholder': '0 = primo, numeri più alti vengono dopo'})
    active = BooleanField('Attiva', default=True)
    submit = SubmitField('Salva Novità')
