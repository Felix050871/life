from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SelectMultipleField, FloatField, DateField, TimeField, TextAreaField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, NumberRange, ValidationError, EqualTo
from models import User, Sede, UserRole

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Ricordami')
    submit = SubmitField('Accedi')

class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password')
    role = SelectField('Ruolo', choices=[], validators=[DataRequired()])
    first_name = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    last_name = StringField('Cognome', validators=[DataRequired(), Length(max=100)])
    sede = SelectField('Sede', coerce=int, validators=[])  # Legacy field
    sedi = SelectMultipleField('Sedi', coerce=int, validators=[DataRequired()])  # New multi-select field
    part_time_percentage = StringField('Percentuale di Lavoro (%)', 
                                     default='100.0')
    is_active = BooleanField('Attivo', default=True)
    submit = SubmitField('Salva Utente')
    
    def __init__(self, original_username=None, is_edit=False, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.is_edit = is_edit
        
        # Popola le scelte delle sedi (per entrambi i campi)
        try:
            from models import Sede as SedeModel
            sedi_attive = SedeModel.query.filter_by(active=True).all()
            self.sede.choices = [(0, 'Nessuna sede')] + [(sede.id, sede.name) for sede in sedi_attive]
            self.sedi.choices = [(sede.id, sede.name) for sede in sedi_attive]
        except:
            self.sede.choices = [(0, 'Nessuna sede')]
            self.sedi.choices = []
        
        # Popola le scelte dei ruoli dinamicamente
        try:
            ruoli_attivi = UserRole.query.filter_by(active=True).all()
            self.role.choices = [(role.name, role.display_name) for role in ruoli_attivi]
            # Fallback ai ruoli legacy se non ci sono ruoli personalizzati
            if not self.role.choices:
                self.role.choices = [
                    ('Admin', 'Admin'),
                    ('Project Manager', 'Project Manager'),
                    ('Redattore', 'Redattore'),
                    ('Sviluppatore', 'Sviluppatore'),
                    ('Operatore', 'Operatore')
                ]
        except:
            self.role.choices = [
                ('Admin', 'Admin'),
                ('Project Manager', 'Project Manager'),
                ('Redattore', 'Redattore'),
                ('Sviluppatore', 'Sviluppatore'),
                ('Operatore', 'Operatore')
            ]
        
        # Set password validators based on mode
        if not is_edit:
            self.password.validators = [DataRequired(), Length(min=6)]
        else:
            self.password.validators = []
    
    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Username già esistente. Scegli un altro username.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user and (not self.original_username or user.username != self.original_username):
            raise ValidationError('Email già esistente. Scegli un\'altra email.')
    
    def validate_sedi(self, sedi):
        # Per utenti Management, le sedi vengono assegnate automaticamente
        if self.role.data == 'Management':
            return
        if not sedi.data:
            raise ValidationError('Seleziona almeno una sede per l\'utente.')
    
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

class AttendanceForm(FlaskForm):
    notes = TextAreaField('Note')
    submit = SubmitField('Registra')

class LeaveRequestForm(FlaskForm):
    start_date = DateField('Data Inizio', validators=[DataRequired()])
    end_date = DateField('Data Fine', validators=[DataRequired()])
    leave_type = SelectField('Tipo', choices=[
        ('Ferie', 'Ferie'),
        ('Permesso', 'Permesso'),
        ('Malattia', 'Malattia')
    ], validators=[DataRequired()])
    reason = TextAreaField('Motivo', validators=[Length(max=500)])
    submit = SubmitField('Invia Richiesta')
    
    def validate_end_date(self, end_date):
        if end_date.data < self.start_date.data:
            raise ValidationError('La data di fine deve essere successiva alla data di inizio.')

class ShiftForm(FlaskForm):
    user_id = SelectField('Utente', coerce=int, validators=[DataRequired()])
    date = DateField('Data', validators=[DataRequired()])
    start_time = TimeField('Ora Inizio', validators=[DataRequired()])
    end_time = TimeField('Ora Fine', validators=[DataRequired()])
    shift_type = SelectField('Tipo Turno', choices=[
        ('Mattina', 'Mattina'),
        ('Pomeriggio', 'Pomeriggio'),
        ('Sera', 'Sera'),
        ('Notte', 'Notte')
    ], validators=[DataRequired()])
    submit = SubmitField('Crea Turno')

class EditShiftForm(FlaskForm):
    """Form per modificare turni esistenti (utente, orari, tipo turno - non data)"""
    user_id = SelectField('Utente', coerce=int, validators=[DataRequired()])
    start_time = TimeField('Ora Inizio', validators=[DataRequired()])
    end_time = TimeField('Ora Fine', validators=[DataRequired()])
    shift_type = SelectField('Tipo Turno', choices=[
        ('Mattina', 'Mattina'),
        ('Pomeriggio', 'Pomeriggio'),
        ('Sera', 'Sera'),
        ('Notte', 'Notte')
    ], validators=[DataRequired()])
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
    required_roles = SelectMultipleField('Ruoli Richiesti', choices=[
        ('Admin', 'Admin'),
        ('Project Manager', 'Project Manager'),
        ('Redattore', 'Redattore'),
        ('Sviluppatore', 'Sviluppatore'),
        ('Operatore', 'Operatore'),
        ('Ente', 'Ente')
    ], validators=[DataRequired()])
    description = StringField('Descrizione', validators=[Length(max=200)])
    is_active = BooleanField('Attivo', default=True)
    submit = SubmitField('Salva Copertura')

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


class ReperibilitaCoverageForm(FlaskForm):
    """Form per creare/modificare coperture reperibilità"""
    start_date = DateField('Data Inizio Validità', validators=[DataRequired()])
    end_date = DateField('Data Fine Validità', validators=[DataRequired()])
    
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
    
    required_roles = SelectMultipleField('Ruoli Richiesti', choices=[
        ('Admin', 'Admin'),
        ('Project Manager', 'Project Manager'),
        ('Redattore', 'Redattore'),
        ('Sviluppatore', 'Sviluppatore'),
        ('Operatore', 'Operatore'),
        ('Ente', 'Ente')
    ], validators=[DataRequired()])
    

    
    description = StringField('Descrizione', validators=[Length(max=200)])
    is_active = BooleanField('Attivo', default=True)
    submit = SubmitField('Salva Copertura')
    
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
    
    def get_role_mapping_dict(self):
        """Converte le selezioni in un dizionario di mappatura ruoli"""
        mapping = {}
        for selection in self.role_mapping.data:
            from_role, to_role = selection.split('->')
            mapping[from_role] = to_role
        return mapping


class ReperibilitaTemplateForm(FlaskForm):
    """Form per generare turnazioni reperibilità"""
    name = StringField('Nome Template', validators=[DataRequired(), Length(max=100)])
    start_date = DateField('Data Inizio', validators=[DataRequired()])
    end_date = DateField('Data Fine', validators=[DataRequired()])
    description = TextAreaField('Descrizione')
    submit = SubmitField('Genera Turnazioni Reperibilità')
    
    def validate_end_date(self, end_date):
        if end_date.data and self.start_date.data and end_date.data < self.start_date.data:
            raise ValidationError('La data di fine deve essere successiva alla data di inizio.')


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
    description = StringField('Descrizione', validators=[Length(max=200)])
    is_active = BooleanField('Attiva', default=True)
    submit = SubmitField('Salva Festività')
    
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
        Length(min=6, message='La password deve essere di almeno 6 caratteri')
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
        Length(min=6, message='La password deve essere di almeno 6 caratteri')
    ])
    confirm_password = PasswordField('Conferma Nuova Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='Le password non corrispondono')
    ])
    submit = SubmitField('Imposta Nuova Password')


class SedeForm(FlaskForm):
    """Form per gestire le sedi aziendali"""
    name = StringField('Nome Sede', validators=[DataRequired(), Length(max=100)])
    address = StringField('Indirizzo', validators=[Length(max=200)])
    description = TextAreaField('Descrizione', validators=[Length(max=500)])
    is_active = BooleanField('Attiva', default=True)
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
    sede = SelectField('Sede', coerce=int, validators=[DataRequired()])
    name = StringField('Nome Orario', validators=[DataRequired(), Length(max=100)])
    start_time = TimeField('Orario Inizio', validators=[DataRequired()])
    end_time = TimeField('Orario Fine', validators=[DataRequired()])
    description = TextAreaField('Descrizione', validators=[Length(max=500)])
    is_active = BooleanField('Attivo', default=True)
    submit = SubmitField('Salva Orario')
    
    def __init__(self, *args, **kwargs):
        super(WorkScheduleForm, self).__init__(*args, **kwargs)
        # Popola le scelte delle sedi attive
        try:
            from models import Sede as SedeModel
            sedi_attive = SedeModel.query.filter_by(active=True).all()
            self.sede.choices = [(sede.id, sede.name) for sede in sedi_attive]
        except:
            self.sede.choices = []
    
    def validate_end_time(self, end_time):
        """Valida che l'orario di fine sia successivo a quello di inizio"""
        if self.start_time.data and end_time.data:
            # Permetti orari che attraversano la mezzanotte
            if end_time.data <= self.start_time.data:
                # Solo se l'orario di fine è minore dell'inizio assumiamo attraversi la mezzanotte
                if end_time.data.hour > self.start_time.data.hour:
                    raise ValidationError('L\'orario di fine deve essere successivo a quello di inizio.')
    
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
    name = StringField('Nome Ruolo (Codice)', validators=[DataRequired(), Length(max=50)])
    display_name = StringField('Nome Visualizzato', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Descrizione', validators=[Length(max=500)])
    
    # Permessi come checkboxes
    can_manage_users = BooleanField('Gestire Utenti')
    can_manage_shifts = BooleanField('Gestire Turni')
    can_approve_leave = BooleanField('Approvare Ferie/Permessi')
    can_request_leave = BooleanField('Richiedere Ferie/Permessi')
    can_access_attendance = BooleanField('Accedere alle Presenze', default=True)
    can_access_dashboard = BooleanField('Accedere alla Dashboard', default=True)
    can_view_reports = BooleanField('Visualizzare Report')
    can_manage_sedi = BooleanField('Gestire Sedi')
    can_manage_roles = BooleanField('Gestire Ruoli')
    
    is_active = BooleanField('Attivo', default=True)
    submit = SubmitField('Salva Ruolo')
    
    def __init__(self, original_name=None, *args, **kwargs):
        super(RoleForm, self).__init__(*args, **kwargs)
        self.original_name = original_name
    
    def validate_name(self, name):
        """Valida che il nome del ruolo sia unico"""
        if name.data != self.original_name:
            role = UserRole.query.filter_by(name=name.data).first()
            if role:
                raise ValidationError('Nome ruolo già esistente. Scegli un altro nome.')
    
    def get_permissions_dict(self):
        """Converte i permessi del form in un dizionario"""
        return {
            'can_manage_users': self.can_manage_users.data,
            'can_manage_shifts': self.can_manage_shifts.data,
            'can_approve_leave': self.can_approve_leave.data,
            'can_request_leave': self.can_request_leave.data,
            'can_access_attendance': self.can_access_attendance.data,
            'can_access_dashboard': self.can_access_dashboard.data,
            'can_view_reports': self.can_view_reports.data,
            'can_manage_sedi': self.can_manage_sedi.data,
            'can_manage_roles': self.can_manage_roles.data
        }
    
    def populate_permissions(self, permissions_dict):
        """Popola i campi permessi dal dizionario"""
        self.can_manage_users.data = permissions_dict.get('can_manage_users', False)
        self.can_manage_shifts.data = permissions_dict.get('can_manage_shifts', False)
        self.can_approve_leave.data = permissions_dict.get('can_approve_leave', False)
        self.can_request_leave.data = permissions_dict.get('can_request_leave', False)
        self.can_access_attendance.data = permissions_dict.get('can_access_attendance', True)
        self.can_access_dashboard.data = permissions_dict.get('can_access_dashboard', True)
        self.can_view_reports.data = permissions_dict.get('can_view_reports', False)
        self.can_manage_sedi.data = permissions_dict.get('can_manage_sedi', False)
        self.can_manage_roles.data = permissions_dict.get('can_manage_roles', False)
