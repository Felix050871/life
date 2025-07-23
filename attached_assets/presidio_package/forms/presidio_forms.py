# Form per Presidio - Sistema Gestione Presenze
# Estratto dal sistema completo per implementazione standalone

from flask_wtf import FlaskForm
from wtforms import (StringField, DateField, TimeField, SelectMultipleField, 
                     IntegerField, SubmitField, TextAreaField, BooleanField)
from wtforms.validators import DataRequired, Length, NumberRange, ValidationError
from datetime import datetime

class PresidioCoverageTemplateForm(FlaskForm):
    """Form per creare/modificare il template di copertura presidio"""
    name = StringField('Nome Template', validators=[
        DataRequired(message='Il nome del template è obbligatorio'), 
        Length(max=100, message='Il nome non può superare 100 caratteri')
    ])
    
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
        ('Admin', 'Admin'),
        ('Project Manager', 'Project Manager'),
        ('Redattore', 'Redattore'),
        ('Sviluppatore', 'Sviluppatore'),
        ('Operatore', 'Operatore'),
        ('Ente', 'Ente')
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

    def validate_break_end(self, break_end):
        """Valida l'ora di fine pausa"""
        # Solo valida se entrambi i campi pause sono compilati
        if break_end.data and break_end.data.strip():
            if not self.break_start.data or not self.break_start.data.strip():
                raise ValidationError('Se inserisci l\'ora di fine pausa, devi inserire anche l\'ora di inizio')
            
            try:
                break_start_time = datetime.strptime(self.break_start.data, '%H:%M').time()
                break_end_time = datetime.strptime(break_end.data, '%H:%M').time()
                
                if break_end_time <= break_start_time:
                    raise ValidationError('L\'ora di fine pausa deve essere successiva all\'ora di inizio pausa')
                
                # Verifica che la pausa sia nell'orario di lavoro
                if self.start_time.data and self.end_time.data:
                    if not (self.start_time.data <= break_start_time <= self.end_time.data and 
                           self.start_time.data <= break_end_time <= self.end_time.data):
                        raise ValidationError('La pausa deve essere compresa nell\'orario di copertura')
                
                # Verifica durata pausa ragionevole (max 2 ore)
                break_duration = (datetime.combine(datetime.today(), break_end_time) - 
                                datetime.combine(datetime.today(), break_start_time)).total_seconds() / 3600
                if break_duration > 2:
                    raise ValidationError('La pausa non può durare più di 2 ore')
                    
            except ValueError:
                raise ValidationError('Formato ora non valido. Usa HH:MM')

    def validate_break_start(self, break_start):
        """Valida l'ora di inizio pausa"""
        if break_start.data and break_start.data.strip():
            if not self.break_end.data or not self.break_end.data.strip():
                raise ValidationError('Se inserisci l\'ora di inizio pausa, devi inserire anche l\'ora di fine')
            
            try:
                datetime.strptime(break_start.data, '%H:%M')
            except ValueError:
                raise ValidationError('Formato ora non valido. Usa HH:MM')

    def validate_required_roles(self, required_roles):
        """Valida che i ruoli selezionati siano validi"""
        valid_roles = ['Admin', 'Project Manager', 'Redattore', 'Sviluppatore', 'Operatore', 'Ente']
        
        for role in required_roles.data:
            if role not in valid_roles:
                raise ValidationError(f'Ruolo non valido: {role}')

class PresidioCoverageSearchForm(FlaskForm):
    """Form per ricercare e filtrare coperture presidio"""
    template_name = StringField('Nome Template', render_kw={
        'class': 'form-control',
        'placeholder': 'Filtra per nome template'
    })
    
    start_date = DateField('Da Data', render_kw={
        'class': 'form-control'
    })
    
    end_date = DateField('A Data', render_kw={
        'class': 'form-control'
    })
    
    day_of_week = SelectMultipleField('Giorni della Settimana', choices=[
        (0, 'Lunedì'),
        (1, 'Martedì'),
        (2, 'Mercoledì'),
        (3, 'Giovedì'),
        (4, 'Venerdì'),
        (5, 'Sabato'),
        (6, 'Domenica')
    ], coerce=int, render_kw={
        'class': 'form-select',
        'multiple': True
    })
    
    required_role = SelectMultipleField('Ruoli Richiesti', choices=[
        ('Admin', 'Admin'),
        ('Project Manager', 'Project Manager'),
        ('Redattore', 'Redattore'),
        ('Sviluppatore', 'Sviluppatore'),
        ('Operatore', 'Operatore'),
        ('Ente', 'Ente')
    ], render_kw={
        'class': 'form-select',
        'multiple': True
    })
    
    is_active = SelectMultipleField('Stato', choices=[
        (True, 'Attive'),
        (False, 'Inattive')
    ], coerce=bool, render_kw={
        'class': 'form-select'
    })
    
    search = SubmitField('Cerca', render_kw={
        'class': 'btn btn-primary'
    })
    
    clear = SubmitField('Pulisci Filtri', render_kw={
        'class': 'btn btn-secondary'
    })