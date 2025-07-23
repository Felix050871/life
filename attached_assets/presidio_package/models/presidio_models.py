# Modelli Database per Presidio - Sistema Gestione Presenze
# Estratto dal sistema completo per implementazione standalone

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

def italian_now():
    """Restituisce l'ora attuale in timezone italiano"""
    from datetime import timezone, timedelta
    italian_tz = timezone(timedelta(hours=2))  # UTC+2 (considerando ora legale)
    return datetime.now(italian_tz).replace(tzinfo=None)

class PresidioCoverageTemplate(db.Model):
    """Template di copertura presidio con nome e periodo di validità"""
    __tablename__ = 'presidio_coverage_template'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Nome del template
    start_date = db.Column(db.Date, nullable=False)   # Data inizio validità
    end_date = db.Column(db.Date, nullable=False)     # Data fine validità
    description = db.Column(db.String(200))           # Descrizione opzionale
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=italian_now)

    # Relazioni
    creator = db.relationship('User', backref='presidio_coverage_templates')
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
    """Definisce la copertura presidio per giorno della settimana e fascia oraria"""
    __tablename__ = 'presidio_coverage'
    
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('presidio_coverage_template.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Lunedì, 1=Martedì, ..., 6=Domenica
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    required_roles = db.Column(db.Text, nullable=False)  # JSON array dei ruoli richiesti per questa fascia
    role_count = db.Column(db.Integer, default=1)       # Numero di persone richieste per ruolo
    break_start = db.Column(db.Time)                     # Ora inizio pausa (opzionale)
    break_end = db.Column(db.Time)                       # Ora fine pausa (opzionale)
    description = db.Column(db.String(200))              # Descrizione opzionale della copertura
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=italian_now)

    def get_day_name(self):
        """Restituisce il nome del giorno in italiano"""
        days = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
        return days[self.day_of_week] if self.day_of_week < len(days) else 'Sconosciuto'
    
    def get_time_range(self):
        """Restituisce la fascia oraria formattata"""
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"
    
    def get_break_range(self):
        """Restituisce la fascia della pausa formattata"""
        if self.break_start and self.break_end:
            return f"{self.break_start.strftime('%H:%M')} - {self.break_end.strftime('%H:%M')}"
        return None
    
    def get_duration_hours(self):
        """Calcola la durata in ore della copertura"""
        from datetime import datetime, timedelta
        
        # Converti time in datetime per calcolare la differenza
        start_dt = datetime.combine(datetime.today(), self.start_time)
        end_dt = datetime.combine(datetime.today(), self.end_time)
        
        # Gestisci il caso in cui end_time sia il giorno dopo (es. turno notturno)
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)
        
        duration = end_dt - start_dt
        return duration.total_seconds() / 3600  # Converti in ore
    
    def get_required_roles(self):
        """Restituisce la lista dei ruoli richiesti dal JSON"""
        try:
            return json.loads(self.required_roles)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_required_roles(self, roles_list):
        """Imposta la lista dei ruoli richiesti come JSON"""
        self.required_roles = json.dumps(roles_list)
    
    def get_required_roles_display(self):
        """Restituisce i ruoli formattati per la visualizzazione"""
        roles = self.get_required_roles()
        if not roles:
            return "Nessun ruolo"
        
        if len(roles) == 1:
            role_display = roles[0]
        elif len(roles) == 2:
            role_display = f"{roles[0]} o {roles[1]}"
        else:
            role_display = f"{', '.join(roles[:-1])} o {roles[-1]}"
        
        if self.role_count > 1:
            role_display += f" (x{self.role_count})"
        
        return role_display

    def is_valid_for_date(self, check_date):
        """Verifica se la copertura è valida per una data specifica tramite il template"""
        return (self.template.start_date <= check_date <= self.template.end_date and 
                self.is_active and self.template.is_active)
    
    def overlaps_with(self, other_coverage):
        """Verifica se questa copertura si sovrappone con un'altra nello stesso giorno"""
        if self.day_of_week != other_coverage.day_of_week:
            return False
        
        # Controlla sovrapposizione oraria
        return not (self.end_time <= other_coverage.start_time or 
                   self.start_time >= other_coverage.end_time)
    
    def get_effective_work_hours(self):
        """Calcola le ore effettive considerando la pausa"""
        total_hours = self.get_duration_hours()
        
        if self.break_start and self.break_end:
            # Calcola durata pausa
            break_start_dt = datetime.combine(datetime.today(), self.break_start)
            break_end_dt = datetime.combine(datetime.today(), self.break_end)
            break_duration = (break_end_dt - break_start_dt).total_seconds() / 3600
            
            total_hours -= break_duration
        
        return max(0, total_hours)  # Non può essere negativa

    def __repr__(self):
        return f'<PresidioCoverage {self.get_day_name()} {self.get_time_range()}>'

# Funzioni di utilità per query comuni
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