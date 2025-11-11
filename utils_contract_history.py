"""
Utility functions for managing contract history
"""
from app import db
from models import ContractHistory, UserHRData, italian_now
from datetime import datetime, timedelta


# Campi contrattuali/economici da tracciare
TRACKED_CONTRACT_FIELDS = [
    'contract_type', 'distacco_supplier', 'consulente_vat', 'nome_fornitore', 
    'partita_iva_fornitore', 'hire_date', 'contract_start_date', 'contract_end_date',
    'probation_end_date', 'ccnl', 'ccnl_level', 'work_hours_week', 'working_time_type',
    'part_time_percentage', 'part_time_type', 'mansione', 'qualifica', 'superminimo',
    'rimborsi_diarie', 'rischio_inail', 'tipo_assunzione', 'ticket_restaurant',
    'other_notes', 'gross_salary', 'net_salary', 'iban', 'payment_method',
    'meal_vouchers_value', 'fuel_card', 'overtime_enabled', 'overtime_type',
    'banca_ore_limite_max', 'banca_ore_periodo_mesi', 'gg_ferie_maturate_mese',
    'hh_permesso_maturate_mese', 'sede_id', 'work_schedule_id'
]


def has_contract_changes(hr_data: UserHRData, previous_snapshot: dict) -> bool:
    """
    Verifica se ci sono stati cambiamenti nei dati contrattuali
    
    Args:
        hr_data: UserHRData object corrente
        previous_snapshot: dizionario con i valori precedenti
        
    Returns:
        True se ci sono modifiche, False altrimenti
    """
    for field in TRACKED_CONTRACT_FIELDS:
        current_value = getattr(hr_data, field, None)
        previous_value = previous_snapshot.get(field)
        
        # Gestione speciale per Decimal/float
        if isinstance(current_value, (int, float)) and isinstance(previous_value, (int, float)):
            if abs(float(current_value or 0) - float(previous_value or 0)) > 0.01:
                return True
        # Confronto standard
        elif current_value != previous_value:
            return True
    
    return False


def get_current_snapshot(hr_data: UserHRData) -> dict:
    """
    Estrae lo snapshot corrente dei dati contrattuali da UserHRData
    
    Args:
        hr_data: UserHRData object
        
    Returns:
        Dizionario con tutti i campi tracciati
    """
    snapshot = {}
    for field in TRACKED_CONTRACT_FIELDS:
        snapshot[field] = getattr(hr_data, field, None)
    return snapshot


def create_contract_snapshot(hr_data: UserHRData, changed_by_user_id: int = None, 
                            notes: str = None, effective_date: datetime = None):
    """
    Crea un nuovo snapshot contrattuale nello storico
    
    Args:
        hr_data: UserHRData object da cui creare lo snapshot
        changed_by_user_id: ID dell'utente che ha fatto la modifica
        notes: Note sulla modifica (opzionale)
        effective_date: Data di validità dello snapshot (default: now)
    """
    if effective_date is None:
        effective_date = italian_now()
    
    # Chiudi il record attivo precedente (se esiste)
    active_record = ContractHistory.query.filter_by(
        user_hr_data_id=hr_data.id,
        effective_to_date=None
    ).first()
    
    if active_record:
        # Imposta la data di fine validità 1 secondo prima del nuovo snapshot
        active_record.effective_to_date = effective_date - timedelta(seconds=1)
        db.session.add(active_record)
    
    # Crea nuovo snapshot
    snapshot = ContractHistory(
        user_hr_data_id=hr_data.id,
        effective_from_date=effective_date,
        effective_to_date=None,  # Record attivo
        changed_by_id=changed_by_user_id,
        changed_at=italian_now(),
        change_notes=notes,
        company_id=hr_data.company_id,
        
        # Dati contrattuali
        contract_type=hr_data.contract_type,
        distacco_supplier=hr_data.distacco_supplier,
        consulente_vat=hr_data.consulente_vat,
        nome_fornitore=hr_data.nome_fornitore,
        partita_iva_fornitore=hr_data.partita_iva_fornitore,
        hire_date=hr_data.hire_date,
        contract_start_date=hr_data.contract_start_date,
        contract_end_date=hr_data.contract_end_date,
        probation_end_date=hr_data.probation_end_date,
        ccnl=hr_data.ccnl,
        ccnl_level=hr_data.ccnl_level,
        work_hours_week=hr_data.work_hours_week,
        working_time_type=hr_data.working_time_type,
        part_time_percentage=hr_data.part_time_percentage,
        part_time_type=hr_data.part_time_type,
        mansione=hr_data.mansione,
        qualifica=hr_data.qualifica,
        superminimo=hr_data.superminimo,
        rimborsi_diarie=hr_data.rimborsi_diarie,
        rischio_inail=hr_data.rischio_inail,
        tipo_assunzione=hr_data.tipo_assunzione,
        ticket_restaurant=hr_data.ticket_restaurant,
        other_notes=hr_data.other_notes,
        
        # Dati economici
        gross_salary=hr_data.gross_salary,
        net_salary=hr_data.net_salary,
        iban=hr_data.iban,
        payment_method=hr_data.payment_method,
        meal_vouchers_value=hr_data.meal_vouchers_value,
        fuel_card=hr_data.fuel_card,
        
        # Dati operativi
        sede_id=hr_data.sede_id,
        work_schedule_id=hr_data.work_schedule_id,
        overtime_enabled=hr_data.overtime_enabled,
        overtime_type=hr_data.overtime_type,
        banca_ore_limite_max=hr_data.banca_ore_limite_max,
        banca_ore_periodo_mesi=hr_data.banca_ore_periodo_mesi,
        gg_ferie_maturate_mese=hr_data.gg_ferie_maturate_mese,
        hh_permesso_maturate_mese=hr_data.hh_permesso_maturate_mese
    )
    
    db.session.add(snapshot)


def save_contract_history_if_changed(hr_data: UserHRData, previous_snapshot: dict, 
                                     changed_by_user_id: int = None, notes: str = None):
    """
    Salva un nuovo snapshot nello storico solo se ci sono stati cambiamenti
    
    Args:
        hr_data: UserHRData object corrente
        previous_snapshot: snapshot precedente (dict)
        changed_by_user_id: ID utente che ha fatto le modifiche
        notes: Note sulla modifica
        
    Returns:
        True se è stato creato un nuovo snapshot, False altrimenti
    """
    if has_contract_changes(hr_data, previous_snapshot):
        create_contract_snapshot(hr_data, changed_by_user_id, notes)
        return True
    return False


def get_contract_history(user_hr_data_id: int, from_date: datetime = None, 
                        to_date: datetime = None, limit: int = None):
    """
    Ottiene lo storico contrattuale di un dipendente
    
    Args:
        user_hr_data_id: ID del record UserHRData
        from_date: Data inizio filtro (opzionale)
        to_date: Data fine filtro (opzionale)
        limit: Numero massimo di record da restituire
        
    Returns:
        Lista di oggetti ContractHistory ordinati per data decrescente
    """
    query = ContractHistory.query.filter_by(user_hr_data_id=user_hr_data_id)
    
    if from_date:
        query = query.filter(ContractHistory.effective_from_date >= from_date)
    
    if to_date:
        query = query.filter(ContractHistory.effective_from_date <= to_date)
    
    query = query.order_by(ContractHistory.effective_from_date.desc())
    
    if limit:
        query = query.limit(limit)
    
    return query.all()


def get_active_contract_snapshot(user_hr_data_id: int):
    """
    Ottiene lo snapshot contrattuale attualmente attivo
    
    Args:
        user_hr_data_id: ID del record UserHRData
        
    Returns:
        ContractHistory object o None
    """
    return ContractHistory.query.filter_by(
        user_hr_data_id=user_hr_data_id,
        effective_to_date=None
    ).first()


def get_changed_fields(current_snapshot: ContractHistory, previous_snapshot: ContractHistory) -> list:
    """
    Confronta due snapshot e restituisce la lista dei campi modificati
    
    Args:
        current_snapshot: Snapshot corrente
        previous_snapshot: Snapshot precedente
        
    Returns:
        Lista di nomi dei campi che sono stati modificati
    """
    if not previous_snapshot:
        return []  # Primo snapshot, nessun confronto possibile
    
    changed_fields = []
    
    for field in TRACKED_CONTRACT_FIELDS:
        current_value = getattr(current_snapshot, field, None)
        previous_value = getattr(previous_snapshot, field, None)
        
        # Gestione speciale per Decimal/float
        if isinstance(current_value, (int, float)) and isinstance(previous_value, (int, float)):
            if abs(float(current_value or 0) - float(previous_value or 0)) > 0.01:
                changed_fields.append(field)
        # Confronto standard
        elif current_value != previous_value:
            changed_fields.append(field)
    
    return changed_fields
