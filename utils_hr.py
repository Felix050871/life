"""
Utility functions for HR operations
"""
from app import db
from models import CompanyHrCounters, UserHRData
from sqlalchemy import select


def assign_cod_si(hr_data):
    """
    Assegna un COD SI auto-incrementato al dipendente.
    
    Implementa un sistema di auto-incremento sicuro per la matricola dipendente
    usando un contatore per company con transaction locking per evitare race conditions.
    
    Args:
        hr_data (UserHRData): Record HR del dipendente a cui assegnare il COD SI
        
    Returns:
        int: Il numero COD SI assegnato
        
    Note:
        - Il COD SI è auto-incrementato per company_id (ogni azienda ha il proprio contatore)
        - Usa SELECT FOR UPDATE per garantire atomicità in caso di accessi concorrenti
        - Crea automaticamente il contatore se non esiste per la company
        - Il numero viene salvato in UserHRData.cod_si_number
        - La visualizzazione formattata (000001) è disponibile via property hr_data.cod_si
    """
    if not hr_data or not hr_data.company_id:
        raise ValueError("UserHRData deve avere company_id valido")
    
    # Verifica se già assegnato
    if hr_data.cod_si_number is not None:
        return hr_data.cod_si_number
    
    # Recupera o crea il contatore per questa company con lock per scrittura
    # SELECT FOR UPDATE previene race conditions bloccando la riga durante la transazione
    counter = db.session.query(CompanyHrCounters).filter_by(
        company_id=hr_data.company_id
    ).with_for_update().first()
    
    if not counter:
        # Se il contatore non esiste, lo creiamo
        # Prima verifica qual è l'ultima matricola esistente per questa company
        max_existing = db.session.query(db.func.max(UserHRData.cod_si_number)).filter(
            UserHRData.company_id == hr_data.company_id,
            UserHRData.cod_si_number.isnot(None)
        ).scalar()
        
        # Inizializza il contatore dal massimo esistente + 1, o da 1 se non ci sono dipendenti
        next_value = (max_existing + 1) if max_existing else 1
        
        counter = CompanyHrCounters(
            company_id=hr_data.company_id,
            next_cod_si=next_value
        )
        db.session.add(counter)
        db.session.flush()  # Assicura che il counter abbia un ID prima di usarlo
    
    # Assegna il numero corrente e incrementa il contatore
    assigned_number = counter.next_cod_si
    hr_data.cod_si_number = assigned_number
    counter.next_cod_si += 1
    
    # Il commit sarà fatto dalla funzione chiamante
    return assigned_number


def initialize_company_hr_counter(company_id):
    """
    Inizializza il contatore HR per una company se non esiste.
    
    Utile per migrazione dati o setup iniziale company.
    
    Args:
        company_id (int): ID della company
        
    Returns:
        CompanyHrCounters: Il contatore creato o esistente
    """
    counter = CompanyHrCounters.query.filter_by(company_id=company_id).first()
    
    if not counter:
        # Trova il massimo COD SI esistente per questa company
        max_existing = db.session.query(db.func.max(UserHRData.cod_si_number)).filter(
            UserHRData.company_id == company_id,
            UserHRData.cod_si_number.isnot(None)
        ).scalar()
        
        next_value = (max_existing + 1) if max_existing else 1
        
        counter = CompanyHrCounters(
            company_id=company_id,
            next_cod_si=next_value
        )
        db.session.add(counter)
        db.session.commit()
    
    return counter


def assign_sequential_matricole(company_id):
    """
    Assegna matricole sequenziali a tutti gli utenti di una company.
    
    Regola di assegnazione:
    - Admin (primo utente): 0000000
    - Altri utenti: 0000001, 0000002, 0000003, ... in ordine di user_id
    
    Aggiorna sia il campo matricola (String) che cod_si_number (Integer).
    
    Args:
        company_id (int): ID della company da processare
        
    Returns:
        dict: Statistiche dell'operazione (processed, updated)
    """
    from models import User
    
    # Trova tutti gli utenti della company ordinati per ID
    users = User.query.filter_by(company_id=company_id).order_by(User.id).all()
    
    stats = {
        'processed': 0,
        'updated': 0
    }
    
    for idx, user in enumerate(users):
        stats['processed'] += 1
        
        # Trova o crea il record HR per questo utente
        hr_data = UserHRData.query.filter_by(user_id=user.id, company_id=company_id).first()
        
        if not hr_data:
            # Crea un nuovo record HR se non esiste
            hr_data = UserHRData(
                user_id=user.id,
                company_id=company_id
            )
            db.session.add(hr_data)
        
        # Assegna il numero progressivo
        # Admin (primo utente) prende 0000000, gli altri partono da 0000001
        matricola_number = idx
        
        # Aggiorna entrambi i campi con formato a 7 caratteri
        hr_data.matricola = f"{matricola_number:07d}"
        hr_data.cod_si_number = matricola_number
        
        stats['updated'] += 1
    
    db.session.commit()
    return stats


def backfill_cod_si_from_matricola(company_id=None):
    """
    Migrazione dati: popola cod_si_number estraendo numeri dal campo matricola (String).
    
    Questa funzione è utile per migrare dati esistenti dal vecchio campo matricola (String)
    al nuovo campo cod_si_number (Integer).
    
    Args:
        company_id (int, optional): Se specificato, processa solo questa company
        
    Returns:
        dict: Statistiche della migrazione (processed, updated, skipped, errors)
    """
    import re
    
    query = UserHRData.query
    if company_id:
        query = query.filter_by(company_id=company_id)
    
    # Prendi solo record con matricola ma senza cod_si_number
    hr_records = query.filter(
        UserHRData.matricola.isnot(None),
        UserHRData.matricola != '',
        UserHRData.cod_si_number.is_(None)
    ).all()
    
    stats = {
        'processed': 0,
        'updated': 0,
        'skipped': 0,
        'errors': []
    }
    
    for hr_data in hr_records:
        stats['processed'] += 1
        
        try:
            # Estrai solo i numeri dalla matricola
            numbers = re.findall(r'\d+', hr_data.matricola)
            
            if numbers:
                # Prendi il primo numero trovato
                cod_si_num = int(numbers[0])
                hr_data.cod_si_number = cod_si_num
                stats['updated'] += 1
            else:
                # Nessun numero trovato nella matricola
                stats['skipped'] += 1
                stats['errors'].append({
                    'user_id': hr_data.user_id,
                    'matricola': hr_data.matricola,
                    'error': 'No numeric value found in matricola'
                })
                
        except Exception as e:
            stats['skipped'] += 1
            stats['errors'].append({
                'user_id': hr_data.user_id,
                'matricola': hr_data.matricola,
                'error': str(e)
            })
    
    db.session.commit()
    return stats


def sync_operational_fields(user, hr_data):
    """
    Sincronizza i campi operativi da UserHRData al modello User.
    
    Questa funzione implementa la strategia di write-through synchronization:
    quando i dati HR vengono salvati, i campi operativi vengono copiati
    anche nel modello User per mantenere backward compatibility con i blueprint
    che ancora leggono da User invece che da UserHRData.
    
    Campi sincronizzati:
    - sede (sede_id)
    - all_sedi
    - work_schedule (work_schedule_id)
    - overtime_enabled
    - overtime_type
    - banca_ore_limite_max
    - banca_ore_periodo_mesi
    - aci_vehicle (aci_vehicle_id)
    - matricola (formattato da cod_si_number a 7 cifre)
    
    Args:
        user (User): Modello User da aggiornare
        hr_data (UserHRData): Record HR sorgente dei dati
        
    Note:
        - UserHRData è la single source of truth per i dati operativi
        - User model mantiene i campi per backward compatibility
        - Questa funzione deve essere chiamata all'interno della stessa transazione del salvataggio HR
        - Non fa commit, lascia la gestione della transazione al chiamante
    """
    if not user or not hr_data:
        return
    
    # Sincronizza sede (assegna all'ID field, non alla relationship)
    user.sede_id = hr_data.sede_id
    
    # Sincronizza accesso a tutte le sedi
    user.all_sedi = hr_data.all_sedi
    
    # Sincronizza orario di lavoro (assegna all'ID field, non alla relationship)
    user.work_schedule_id = hr_data.work_schedule_id
    
    # Sincronizza veicolo ACI (assegna all'ID field, non alla relationship)
    user.aci_vehicle_id = hr_data.aci_vehicle_id
    
    # Sincronizza impostazioni straordinari
    user.overtime_enabled = hr_data.overtime_enabled
    user.overtime_type = hr_data.overtime_type
    user.banca_ore_limite_max = hr_data.banca_ore_limite_max
    user.banca_ore_periodo_mesi = hr_data.banca_ore_periodo_mesi
    
    # Sincronizza matricola (formatta cod_si_number a 7 cifre per export XML)
    if hr_data.cod_si_number is not None:
        user.matricola = f"{hr_data.cod_si_number:07d}"
    else:
        user.matricola = None
    
    # Non facciamo commit qui - sarà fatto dal chiamante
