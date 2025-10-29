"""
Service layer per la gestione della vista timesheet mensile.
Fornisce una vista normalizzata per giorno senza complessità di rowspan.
"""
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
from models import (
    MonthlyTimesheet, AttendanceSession, AttendanceEvent, 
    LeaveRequest, AttendanceType, Sede, Commessa
)
from utils import filter_by_company


def calculate_hours(start_time_str: Optional[str], end_time_str: Optional[str]) -> float:
    """
    Calcola le ore tra due orari in formato "HH:MM".
    Returns 0.0 se uno dei due orari è None.
    """
    if not start_time_str or not end_time_str:
        return 0.0
    
    try:
        start_parts = start_time_str.split(':')
        end_parts = end_time_str.split(':')
        
        start_hours = int(start_parts[0])
        start_minutes = int(start_parts[1])
        end_hours = int(end_parts[0])
        end_minutes = int(end_parts[1])
        
        start_total_minutes = start_hours * 60 + start_minutes
        end_total_minutes = end_hours * 60 + end_minutes
        
        diff_minutes = end_total_minutes - start_total_minutes
        if diff_minutes < 0:  # Se attraversa la mezzanotte
            diff_minutes += 24 * 60
        
        return round(diff_minutes / 60.0, 1)
    except (ValueError, IndexError):
        return 0.0


@dataclass
class LeaveBlock:
    """Rappresenta un'assenza (permesso/malattia/ferie) per un giorno"""
    leave_type: str
    start_time: Optional[str]  # "09:00" se permesso parziale
    end_time: Optional[str]    # "13:00" se permesso parziale
    is_validated: bool
    highlight_class: str  # "warning" se non validato, "" altrimenti
    total_hours: float  # Ore totali calcolate dagli orari


@dataclass
class SessionRow:
    """Rappresenta una singola sessione di lavoro (o riga vuota per input)"""
    session_id: Optional[int]  # None per righe nuove
    sede_id: Optional[int]
    sede_name: str
    commessa_id: Optional[int]
    commessa_display: str
    attendance_type_id: Optional[int]
    attendance_type_name: str
    clock_in: str  # "08:00"
    break_start: str
    break_end: str
    clock_out: str
    total_hours: float
    source: str  # "manual", "auto", "empty"
    can_delete: bool  # True solo per righe nuove non salvate
    is_editable: bool  # False se consolidato o futuro


@dataclass
class DayRow:
    """Rappresenta un giorno completo con tutte le sue sessioni"""
    day_num: int  # 1-31
    date_obj: date
    weekday_name: str  # "Lunedì"
    date_display: str  # "28/10/2025"
    is_weekend: bool
    is_holiday: bool
    is_future: bool
    is_editable: bool
    can_add_session: bool
    leave_block: Optional[LeaveBlock]
    sessions: List[SessionRow]
    day_total_hours: float


def build_timesheet_grid(
    timesheet: MonthlyTimesheet,
    user,
    year: int,
    month: int,
    user_sedi: List,
    active_commesse: List,
    attendance_types: List
) -> List[DayRow]:
    """
    Costruisce la griglia completa del timesheet per un mese.
    Ogni giorno viene rappresentato con tutte le sue sessioni in un formato flat.
    
    Returns:
        Lista di DayRow ordinati per data (1-31)
    """
    from calendar import monthrange
    from models import Holiday, WorkSchedule
    
    italian_weekdays = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
    
    # Carica tutti i dati necessari in batch
    company_id = user.company_id
    _, days_in_month = monthrange(year, month)
    
    # Carica esplicitamente il work_schedule dell'utente se presente
    user_work_schedule = None
    if user.work_schedule_id:
        user_work_schedule = WorkSchedule.query.get(user.work_schedule_id)
    
    # Carica sessioni esistenti
    sessions_query = AttendanceSession.query.filter_by(
        timesheet_id=timesheet.id
    ).order_by(AttendanceSession.date, AttendanceSession.start_time).all()
    
    sessions_by_day = {}
    for session in sessions_query:
        day = session.date.day
        if day not in sessions_by_day:
            sessions_by_day[day] = []
        sessions_by_day[day].append(session)
    
    # Carica eventi (timbrature)
    events_query = AttendanceEvent.query.filter_by(
        user_id=user.id,
        company_id=company_id
    ).filter(
        AttendanceEvent.date >= date(year, month, 1),
        AttendanceEvent.date <= date(year, month, days_in_month)
    ).order_by(AttendanceEvent.date, AttendanceEvent.timestamp).all()
    
    events_by_day = {}
    for event in events_query:
        day = event.date.day
        if day not in events_by_day:
            events_by_day[day] = []
        events_by_day[day].append(event)
    
    # Carica permessi/assenze
    leave_requests = LeaveRequest.query.filter_by(
        user_id=user.id,
        company_id=company_id
    ).filter(
        LeaveRequest.start_date <= date(year, month, days_in_month),
        LeaveRequest.end_date >= date(year, month, 1)
    ).all()
    
    leave_by_day = {}
    for leave in leave_requests:
        current = max(leave.start_date, date(year, month, 1))
        end = min(leave.end_date, date(year, month, days_in_month))
        
        while current <= end:
            if current.month == month:
                day = current.day
                # Determina orari dell'assenza
                # Se specificati nel permesso, usa quelli
                # Altrimenti usa gli orari di default del work_schedule dell'utente PER TUTTI I GIORNI
                start_time_str = None
                end_time_str = None
                
                # Orario di inizio
                if leave.start_time and current == leave.start_date:
                    # Usa orario esplicito sul primo giorno se specificato
                    start_time_str = leave.start_time.strftime('%H:%M')
                elif user_work_schedule and user_work_schedule.start_time_min:
                    # Usa orario di inizio dal work schedule su tutti i giorni
                    start_time_str = user_work_schedule.start_time_min.strftime('%H:%M')
                
                # Orario di fine
                if leave.end_time and current == leave.end_date:
                    # Usa orario esplicito sull'ultimo giorno se specificato
                    end_time_str = leave.end_time.strftime('%H:%M')
                elif user_work_schedule and user_work_schedule.end_time_max:
                    # Usa orario di fine dal work schedule su tutti i giorni
                    end_time_str = user_work_schedule.end_time_max.strftime('%H:%M')
                
                # Calcola le ore totali dall'orario di inizio e fine
                # Se non ci sono orari espliciti, usa 8.0 ore come default per giornata intera
                total_hours = calculate_hours(start_time_str, end_time_str)
                if total_hours == 0.0 and not leave.start_time and not leave.end_time:
                    # Assenza/malattia giornata intera senza orari espliciti = 8 ore
                    total_hours = 8.0
                
                leave_by_day[day] = LeaveBlock(
                    leave_type=leave.leave_type_obj.name if leave.leave_type_obj else (leave.leave_type or "Assenza"),
                    start_time=start_time_str,
                    end_time=end_time_str,
                    is_validated=(leave.status == 'Approved'),
                    highlight_class="table-warning" if leave.status != 'Approved' else "",
                    total_hours=total_hours
                )
            current += timedelta(days=1)
    
    # Carica festività (Holiday usa month/day non date e non ha company_id)
    # Le festività sono filtrate tramite sede o sono nazionali (sede_id NULL)
    user_sede_ids = [s.id for s in user_sedi] if user_sedi else []
    holidays_query = Holiday.query.filter_by(
        month=month,
        active=True
    )
    if user_sede_ids:
        from sqlalchemy import or_
        holidays_query = holidays_query.filter(
            or_(
                Holiday.sede_id.in_(user_sede_ids),
                Holiday.sede_id.is_(None)  # Festività nazionali
            )
        )
    else:
        holidays_query = holidays_query.filter(Holiday.sede_id.is_(None))
    
    holidays = holidays_query.all()
    holiday_days = {h.day for h in holidays}
    
    # Costruisci la griglia giorno per giorno
    grid = []
    today = date.today()
    can_edit_timesheet = timesheet.can_edit()
    
    default_type = next((t for t in attendance_types if t.is_default), None)
    
    for day_num in range(1, days_in_month + 1):
        day_date = date(year, month, day_num)
        weekday_name = italian_weekdays[day_date.weekday()]
        is_weekend = day_date.weekday() >= 5
        is_holiday = day_num in holiday_days
        is_future = day_date > today
        
        # Determina se il giorno è editabile
        is_editable = can_edit_timesheet and not is_future
        
        # Determina se si possono aggiungere sessioni
        # Blocca weekend/festivi se l'utente non è abilitato
        can_add = is_editable and not is_future
        if (is_weekend or is_holiday) and not getattr(user, 'can_work_weekends', False):
            can_add = False
        
        # Costruisci le sessioni per questo giorno
        sessions = []
        day_sessions = sessions_by_day.get(day_num, [])
        
        if day_sessions:
            # Sessioni manuali esistenti
            for session in day_sessions:
                sede_name = ""
                if session.sede_id:
                    sede_obj = next((s for s in user_sedi if s.id == session.sede_id), None)
                    if sede_obj:
                        sede_name = sede_obj.name
                
                commessa_display = "N/A"
                if session.commessa_id:
                    comm_obj = next((c for c in active_commesse if c.id == session.commessa_id), None)
                    if comm_obj:
                        commessa_display = f"{comm_obj.codice} - {comm_obj.cliente}"
                
                type_name = ""
                if session.attendance_type_id:
                    type_obj = next((t for t in attendance_types if t.id == session.attendance_type_id), None)
                    if type_obj:
                        type_name = type_obj.name
                
                sessions.append(SessionRow(
                    session_id=session.id,
                    sede_id=session.sede_id,
                    sede_name=sede_name,
                    commessa_id=session.commessa_id,
                    commessa_display=commessa_display,
                    attendance_type_id=session.attendance_type_id,
                    attendance_type_name=type_name,
                    clock_in=session.start_time.strftime('%H:%M') if session.start_time else '',
                    break_start='',  # TODO: gestire pause
                    break_end='',
                    clock_out=session.end_time.strftime('%H:%M') if session.end_time else '',
                    total_hours=session.duration_hours or 0.0,
                    source='manual',
                    can_delete=is_editable,  # Sessioni manuali eliminabili se modificabili
                    is_editable=is_editable
                ))
        elif events_by_day.get(day_num) and not day_sessions:
            # Eventi timbratura senza sessioni manuali - raggruppa in coppie
            day_events = events_by_day[day_num]
            clock_ins = [e for e in day_events if e.event_type == 'clock_in']
            clock_outs = [e for e in day_events if e.event_type == 'clock_out']
            break_starts = [e for e in day_events if e.event_type == 'break_start']
            break_ends = [e for e in day_events if e.event_type == 'break_end']
            
            # Crea una sessione per ogni coppia clock_in/clock_out
            num_pairs = max(len(clock_ins), len(clock_outs))
            if num_pairs > 0:
                for i in range(num_pairs):
                    clock_in = clock_ins[i] if i < len(clock_ins) else None
                    clock_out = clock_outs[i] if i < len(clock_outs) else None
                    # Per semplicità, associa pause alla prima sessione
                    break_start = break_starts[0] if i == 0 and break_starts else None
                    break_end = break_ends[0] if i == 0 and break_ends else None
                    
                    # Calcola ore
                    total_hours = 0.0
                    if clock_in and clock_out:
                        work_time = (clock_out.timestamp - clock_in.timestamp).total_seconds() / 3600
                        if break_start and break_end:
                            break_time = (break_end.timestamp - break_start.timestamp).total_seconds() / 3600
                            work_time -= break_time
                        total_hours = max(0, work_time)
                    
                    sede_name = ""
                    if user.sede_id:
                        sede_obj = next((s for s in user_sedi if s.id == user.sede_id), None)
                        if sede_obj:
                            sede_name = sede_obj.name
                    
                    sessions.append(SessionRow(
                        session_id=None,
                        sede_id=user.sede_id,
                        sede_name=sede_name,
                        commessa_id=None,
                        commessa_display="N/A",
                        attendance_type_id=default_type.id if default_type else None,
                        attendance_type_name=default_type.name if default_type else "",
                        clock_in=clock_in.timestamp.strftime('%H:%M') if clock_in else '',
                        break_start=break_start.timestamp.strftime('%H:%M') if break_start else '',
                        break_end=break_end.timestamp.strftime('%H:%M') if break_end else '',
                        clock_out=clock_out.timestamp.strftime('%H:%M') if clock_out else '',
                        total_hours=total_hours,
                        source='auto',
                        can_delete=False,
                        is_editable=is_editable
                    ))
        elif not is_weekend and not is_holiday and day_num not in leave_by_day:
            # Giorno lavorativo vuoto - crea riga vuota
            sede_name = ""
            if user.sede_id:
                sede_obj = next((s for s in user_sedi if s.id == user.sede_id), None)
                if sede_obj:
                    sede_name = sede_obj.name
            
            sessions.append(SessionRow(
                session_id=None,
                sede_id=user.sede_id,
                sede_name=sede_name,
                commessa_id=None,
                commessa_display="N/A",
                attendance_type_id=default_type.id if default_type else None,
                attendance_type_name=default_type.name if default_type else "",
                clock_in='',
                break_start='',
                break_end='',
                clock_out='',
                total_hours=0.0,
                source='empty',
                can_delete=False,
                is_editable=is_editable
            ))
        
        # Calcola totale ore giornaliere
        day_total = sum(s.total_hours for s in sessions)
        
        grid.append(DayRow(
            day_num=day_num,
            date_obj=day_date,
            weekday_name=weekday_name,
            date_display=day_date.strftime('%d/%m/%Y'),
            is_weekend=is_weekend,
            is_holiday=is_holiday,
            is_future=is_future,
            is_editable=is_editable,
            can_add_session=can_add,
            leave_block=leave_by_day.get(day_num),
            sessions=sessions if sessions else [],
            day_total_hours=day_total
        ))
    
    return grid
