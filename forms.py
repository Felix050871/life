from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SelectMultipleField, FloatField, DateField, TimeField, TextAreaField, SubmitField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Email, Length, NumberRange, ValidationError, EqualTo, Optional
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
    sede = SelectField('Sede', coerce=int, validators=[])
    all_sedi = BooleanField('Accesso a tutte le sedi', default=False)
    work_schedule = SelectField('Orario di Lavoro', coerce=lambda x: int(x) if x and x != '' else None, validators=[Optional()], validate_choice=False)
    part_time_percentage = StringField('Percentuale di Lavoro (%)', 
                                     default='100.0')
    is_active = BooleanField('Attivo', default=True)
    submit = SubmitField('Salva Utente')
    
    def __init__(self, original_username=None, is_edit=False, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.is_edit = is_edit
        
        # Popola le scelte delle sedi
        try:
            from models import Sede as SedeModel
            sedi_attive = SedeModel.query.filter_by(active=True).all()
            self.sede.choices = [(-1, 'Seleziona una sede')] + [(sede.id, sede.name) for sede in sedi_attive]
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
                print(f"Errore nel caricamento work_schedule: {e}")
        
        # Popola le scelte dei ruoli dinamicamente
        try:
            ruoli_attivi = UserRole.query.filter_by(active=True).all()
            self.role.choices = [(role.name, role.display_name) for role in ruoli_attivi]
            # Se non ci sono ruoli personalizzati, inizializza con lista vuota
            if not self.role.choices:
                self.role.choices = []
        except:
            self.role.choices = []
        
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
    
    def validate_sede(self, sede):
        # Se all_sedi è False, deve essere selezionata una sede specifica
        if not self.all_sedi.data and (not sede.data or sede.data == -1):
            raise ValidationError('Seleziona una sede o abilita "Accesso a tutte le sedi".')
        # Se all_sedi è True, non è necessaria una sede specifica
        if self.all_sedi.data:
            return
    
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

class AttendanceForm(FlaskForm):
    notes = TextAreaField('Note')
    submit = SubmitField('Registra')

class LeaveRequestForm(FlaskForm):
    leave_type = SelectField('Tipo Richiesta', choices=[
        ('', 'Seleziona tipo richiesta'),
        ('Ferie', 'Ferie'),
        ('Permesso', 'Permesso'),
        ('Malattia', 'Malattia')
    ], validators=[DataRequired()])
    
    # Campi per date (sempre presenti)
    start_date = DateField('Data Inizio', validators=[DataRequired()])
    end_date = DateField('Data Fine', validators=[Optional()])
    
    # Campi per orari (solo per permessi)
    start_time = TimeField('Ora Inizio', validators=[Optional()])
    end_time = TimeField('Ora Fine', validators=[Optional()])
    
    reason = TextAreaField('Motivo', validators=[Length(max=500)])
    submit = SubmitField('Invia Richiesta')
    
    def validate_start_date(self, field):
        from datetime import date
        if field.data and field.data < date.today():
            raise ValidationError('La data di inizio non può essere nel passato.')
    
    def validate_end_date(self, end_date):
        from datetime import date
        if end_date.data and end_date.data < date.today():
            raise ValidationError('La data di fine non può essere nel passato.')
        if self.leave_type.data in ['Ferie', 'Malattia'] and end_date.data and end_date.data < self.start_date.data:
            raise ValidationError('La data di fine deve essere successiva alla data di inizio.')
    
    def validate_start_time(self, start_time):
        if self.leave_type.data == 'Permesso' and not start_time.data:
            raise ValidationError('L\'ora di inizio è richiesta per i permessi.')
    
    def validate_end_time(self, end_time):
        if self.leave_type.data == 'Permesso':
            if not end_time.data:
                raise ValidationError('L\'ora di fine è richiesta per i permessi.')
            if self.start_time.data and end_time.data <= self.start_time.data:
                raise ValidationError('L\'ora di fine deve essere successiva all\'ora di inizio.')
    
    def validate_end_date_for_permission(self, end_date):
        if self.leave_type.data == 'Permesso' and end_date.data and end_date.data != self.start_date.data:
            raise ValidationError('I permessi devono essere richiesti per una sola giornata.')

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
    is_active = BooleanField('Attivo', default=True)
    submit = SubmitField('Salva Copertura')
    
    def __init__(self, *args, **kwargs):
        super(PresidioCoverageForm, self).__init__(*args, **kwargs)
        # Popola i ruoli dinamicamente dal database, escludendo Admin
        from models import UserRole
        try:
            roles = UserRole.query.filter(UserRole.name != 'Admin').all()
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
    is_active = BooleanField('Attivo', default=True)
    submit = SubmitField('Salva Copertura')
    
    def __init__(self, *args, **kwargs):
        super(ReperibilitaCoverageForm, self).__init__(*args, **kwargs)
        # Popola i ruoli dinamicamente dal database, escludendo Admin
        from models import UserRole, Sede
        try:
            # Popola ruoli escludendo Admin
            roles = UserRole.query.filter(UserRole.name != 'Admin').all()
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
            coverages = ReperibilitaCoverage.query.filter(
                ReperibilitaCoverage.is_active == True,
                ReperibilitaCoverage.end_date >= date.today()
            ).all()
            
            # Crea un dizionario raggruppato per periodo
            periods = {}
            for coverage in coverages:
                period_key = f"{coverage.start_date.strftime('%Y-%m-%d')}__{coverage.end_date.strftime('%Y-%m-%d')}"
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
    is_active = BooleanField('Attiva', default=True)
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
    tipologia = SelectField('Tipologia Sede', choices=[
        ('Oraria', 'Oraria - Gestione basata su orari'),
        ('Turni', 'Turni - Gestione basata su turnazioni')
    ], default='Oraria', validators=[DataRequired()])
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
    can_manage_shifts = BooleanField('Gestire Turni')
    can_view_shifts = BooleanField('Visualizzare Turni')
    
    # Reperibilità
    can_manage_reperibilita = BooleanField('Gestire Reperibilità')
    can_view_reperibilita = BooleanField('Visualizzare Reperibilità')
    can_manage_coverage = BooleanField('Gestire Coperture Reperibilità')
    can_view_coverage = BooleanField('Visualizzare Coperture Reperibilità')
    
    # Gestione presenze
    can_manage_attendance = BooleanField('Gestire Presenze')
    can_view_attendance = BooleanField('Visualizzare Presenze')
    can_access_attendance = BooleanField('Accedere alle Presenze', default=True)
    can_view_sede_attendance = BooleanField('Visualizzare Presenze Sede')
    
    # Gestione ferie/permessi
    can_manage_leave = BooleanField('Gestire Ferie/Permessi')
    can_approve_leave = BooleanField('Approvare Ferie/Permessi')
    can_request_leave = BooleanField('Richiedere Ferie/Permessi')
    can_view_leave = BooleanField('Visualizzare Ferie/Permessi')
    
    # Gestione interventi
    can_manage_interventions = BooleanField('Gestire Interventi')
    can_view_interventions = BooleanField('Visualizzare Interventi')
    
    # Gestione festività
    can_manage_holidays = BooleanField('Gestire Festività')
    can_view_holidays = BooleanField('Visualizzare Festività')
    
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
    can_view_my_reperibilita_widget = BooleanField('Widget La Mia Reperibilità')
    
    is_active = BooleanField('Attivo', default=True)
    submit = SubmitField('Salva Ruolo')
    
    def __init__(self, original_name=None, widget_only=False, *args, **kwargs):
        super(RoleForm, self).__init__(*args, **kwargs)
        self.original_name = original_name
        self.widget_only = widget_only
        
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
            role = UserRole.query.filter_by(name=name.data).first()
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
            'can_manage_coverage': self.can_manage_coverage.data,
            'can_view_coverage': self.can_view_coverage.data,
            
            # Gestione presenze
            'can_manage_attendance': self.can_manage_attendance.data,
            'can_view_attendance': self.can_view_attendance.data,
            'can_access_attendance': self.can_access_attendance.data,
            'can_view_sede_attendance': self.can_view_sede_attendance.data,
            
            # Gestione ferie/permessi
            'can_manage_leave': self.can_manage_leave.data,
            'can_approve_leave': self.can_approve_leave.data,
            'can_request_leave': self.can_request_leave.data,
            'can_view_leave': self.can_view_leave.data,
            
            # Gestione interventi
            'can_manage_interventions': self.can_manage_interventions.data,
            'can_view_interventions': self.can_view_interventions.data,
            
            # Gestione festività
            'can_manage_holidays': self.can_manage_holidays.data,
            'can_view_holidays': self.can_view_holidays.data,
            
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
            'can_view_my_reperibilita_widget': self.can_view_my_reperibilita_widget.data
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
        
        # Gestione presenze
        self.can_manage_attendance.data = permissions_dict.get('can_manage_attendance', False)
        self.can_view_attendance.data = permissions_dict.get('can_view_attendance', False)
        self.can_access_attendance.data = permissions_dict.get('can_access_attendance', True)
        self.can_view_sede_attendance.data = permissions_dict.get('can_view_sede_attendance', False)
        
        # Gestione ferie/permessi
        self.can_manage_leave.data = permissions_dict.get('can_manage_leave', False)
        self.can_approve_leave.data = permissions_dict.get('can_approve_leave', False)
        self.can_request_leave.data = permissions_dict.get('can_request_leave', False)
        self.can_view_leave.data = permissions_dict.get('can_view_leave', False)
        
        # Gestione interventi
        self.can_manage_interventions.data = permissions_dict.get('can_manage_interventions', False)
        self.can_view_interventions.data = permissions_dict.get('can_view_interventions', False)
        
        # Gestione festività
        self.can_manage_holidays.data = permissions_dict.get('can_manage_holidays', False)
        self.can_view_holidays.data = permissions_dict.get('can_view_holidays', False)
        
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
    
    is_active = BooleanField('Attiva', default=True)
    
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
            if duration > 16:  # Massimo 16 ore consecutive
                raise ValidationError('La copertura non può durare più di 16 ore consecutive')

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
    
    is_active = SelectField('Stato', choices=[
        ('', 'Tutti'),
        ('true', 'Attivo'),
        ('false', 'Inattivo')
    ], render_kw={
        'class': 'form-select'
    })
    
    submit = SubmitField('Cerca')
