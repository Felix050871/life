# =============================================================================
# HR (HUMAN RESOURCES) BLUEPRINT
# =============================================================================
#
# ROUTES INCLUSE:
# 1. hr_list (GET) - Lista dipendenti con dati HR
# 2. hr_detail (GET/POST) - Visualizza/modifica scheda HR completa
# 3. hr_export (GET) - Export Excel dati HR
#
# Total routes: 3
# =============================================================================

from flask import Blueprint, request, render_template, redirect, url_for, flash, make_response
from flask_login import login_required, current_user
from datetime import datetime, date
from functools import wraps
from app import db
from models import User, UserHRData, ACITable, Sede
from utils_tenant import filter_by_company, set_company_on_create
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# Create blueprint
hr_bp = Blueprint('hr', __name__, url_prefix='/hr')

# Helper functions
def require_hr_permission(f):
    """Decorator per richiedere permessi HR"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.can_access_hr_menu():
            flash('Non hai i permessi per accedere a questa sezione', 'error')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# HR ROUTES
# =============================================================================

@hr_bp.route('/')
@login_required
@require_hr_permission
def hr_list():
    """Lista dipendenti con dati HR"""
    
    # Ottieni tutti gli utenti con dati HR
    if current_user.can_view_hr_data() or current_user.can_manage_hr_data():
        # HR Manager vedono tutti i dipendenti della company
        users_query = filter_by_company(User.query).filter_by(active=True).order_by(User.last_name, User.first_name)
    else:
        # Utenti normali vedono solo i propri dati (con filtro company)
        users_query = filter_by_company(User.query).filter_by(id=current_user.id)
    
    users = users_query.all()
    
    # Crea dizionario con dati HR per ogni utente
    users_data = []
    for user in users:
        hr_data = user.hr_data
        
        users_data.append({
            'user': user,
            'hr_data': hr_data,  # Pass the actual object so template can access sede relationship
            'has_data': hr_data is not None,
            'matricola': hr_data.matricola if hr_data else '-',
            'contract_type': hr_data.contract_type if hr_data else '-',
            'hire_date': hr_data.hire_date.strftime('%d/%m/%Y') if hr_data and hr_data.hire_date else '-',
            'contract_status': 'Attivo' if hr_data and hr_data.is_contract_active() else 'Non attivo' if hr_data else '-',
            'is_probation': hr_data.is_probation_period() if hr_data else False
        })
    
    return render_template('hr_list.html', users_data=users_data)


@hr_bp.route('/detail/<int:user_id>', methods=['GET', 'POST'])
@login_required
@require_hr_permission
def hr_detail(user_id):
    """Visualizza/modifica scheda HR completa di un utente"""
    
    # Ottieni l'utente
    user = filter_by_company(User.query).filter_by(id=user_id).first_or_404()
    
    # Controllo permessi
    can_edit = current_user.can_manage_hr_data()
    can_view_all = current_user.can_view_hr_data() or current_user.can_manage_hr_data()
    
    # Se non può vedere tutti i dati, può vedere solo i propri
    if not can_view_all and user.id != current_user.id:
        flash('Non hai i permessi per visualizzare questi dati', 'error')
        return redirect(url_for('hr.hr_list'))
    
    # Ottieni record HR esistente
    hr_data = user.hr_data
    
    # Crea record HR solo se l'utente ha permessi di modifica
    if not hr_data and can_edit:
        hr_data = UserHRData(user_id=user.id, company_id=user.company_id)
        set_company_on_create(hr_data)
        db.session.add(hr_data)
        db.session.commit()
    elif not hr_data:
        # Per utenti read-only, crea oggetto vuoto non persistito
        # in modo che il template possa accedere agli attributi senza errori
        hr_data = UserHRData(user_id=user.id, company_id=user.company_id)
    
    if request.method == 'POST' and can_edit:
        try:
            # Aggiorna dati anagrafici
            hr_data.matricola = request.form.get('matricola', '').strip() or None
            hr_data.codice_fiscale = request.form.get('codice_fiscale', '').strip().upper() or None
            hr_data.gender = request.form.get('gender', '') or None
            
            # Data nascita
            birth_date_str = request.form.get('birth_date', '').strip()
            if birth_date_str:
                hr_data.birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
            
            hr_data.birth_city = request.form.get('birth_city', '').strip() or None
            hr_data.birth_province = request.form.get('birth_province', '').strip().upper() or None
            hr_data.birth_country = request.form.get('birth_country', '').strip() or 'Italia'
            
            # Residenza e contatti
            hr_data.address = request.form.get('address', '').strip() or None
            hr_data.city = request.form.get('city', '').strip() or None
            hr_data.province = request.form.get('province', '').strip().upper() or None
            hr_data.postal_code = request.form.get('postal_code', '').strip() or None
            hr_data.country = request.form.get('country', '').strip() or 'Italia'
            hr_data.alternative_domicile = request.form.get('alternative_domicile', '').strip() or None
            hr_data.phone = request.form.get('phone', '').strip() or None
            hr_data.law_104_benefits = request.form.get('law_104_benefits') == 'on'
            
            # Dati contrattuali
            hr_data.contract_type = request.form.get('contract_type', '').strip() or None
            
            hire_date_str = request.form.get('hire_date', '').strip()
            if hire_date_str:
                hr_data.hire_date = datetime.strptime(hire_date_str, '%Y-%m-%d').date()
            
            contract_start_str = request.form.get('contract_start_date', '').strip()
            if contract_start_str:
                hr_data.contract_start_date = datetime.strptime(contract_start_str, '%Y-%m-%d').date()
            
            contract_end_str = request.form.get('contract_end_date', '').strip()
            if contract_end_str:
                hr_data.contract_end_date = datetime.strptime(contract_end_str, '%Y-%m-%d').date()
            else:
                hr_data.contract_end_date = None
            
            probation_end_str = request.form.get('probation_end_date', '').strip()
            if probation_end_str:
                hr_data.probation_end_date = datetime.strptime(probation_end_str, '%Y-%m-%d').date()
            else:
                hr_data.probation_end_date = None
            
            hr_data.ccnl = request.form.get('ccnl', '').strip() or None
            hr_data.ccnl_level = request.form.get('ccnl_level', '').strip() or None
            hr_data.mansione = request.form.get('mansione', '').strip() or None
            hr_data.qualifica = request.form.get('qualifica', '').strip() or None
            hr_data.cliente = request.form.get('cliente', '').strip() or None
            hr_data.rischio_inail = request.form.get('rischio_inail', '').strip() or None
            hr_data.tipo_assunzione = request.form.get('tipo_assunzione', '').strip() or None
            hr_data.ticket_restaurant = request.form.get('ticket_restaurant') == 'on'
            hr_data.other_notes = request.form.get('other_notes', '').strip() or None
            
            work_hours_str = request.form.get('work_hours_week', '').strip()
            if work_hours_str:
                hr_data.work_hours_week = float(work_hours_str.replace(',', '.'))
            
            superminimo_str = request.form.get('superminimo', '').strip()
            if superminimo_str:
                hr_data.superminimo = float(superminimo_str.replace(',', '.'))
            
            rimborsi_str = request.form.get('rimborsi_diarie', '').strip()
            if rimborsi_str:
                hr_data.rimborsi_diarie = float(rimborsi_str.replace(',', '.'))
            
            # Dati economici
            gross_salary_str = request.form.get('gross_salary', '').strip()
            if gross_salary_str:
                hr_data.gross_salary = float(gross_salary_str.replace(',', '.'))
            
            net_salary_str = request.form.get('net_salary', '').strip()
            if net_salary_str:
                hr_data.net_salary = float(net_salary_str.replace(',', '.'))
            
            hr_data.iban = request.form.get('iban', '').strip().upper() or None
            hr_data.payment_method = request.form.get('payment_method', '').strip() or None
            
            # Documenti
            hr_data.id_card_type = request.form.get('id_card_type', '').strip() or None
            hr_data.id_card_number = request.form.get('id_card_number', '').strip() or None
            
            id_issue_str = request.form.get('id_card_issue_date', '').strip()
            if id_issue_str:
                hr_data.id_card_issue_date = datetime.strptime(id_issue_str, '%Y-%m-%d').date()
            
            id_expiry_str = request.form.get('id_card_expiry', '').strip()
            if id_expiry_str:
                hr_data.id_card_expiry = datetime.strptime(id_expiry_str, '%Y-%m-%d').date()
            
            hr_data.id_card_issued_by = request.form.get('id_card_issued_by', '').strip() or None
            hr_data.passport_number = request.form.get('passport_number', '').strip() or None
            
            passport_expiry_str = request.form.get('passport_expiry', '').strip()
            if passport_expiry_str:
                hr_data.passport_expiry = datetime.strptime(passport_expiry_str, '%Y-%m-%d').date()
            
            # Contatto emergenza
            hr_data.emergency_contact_name = request.form.get('emergency_contact_name', '').strip() or None
            hr_data.emergency_contact_phone = request.form.get('emergency_contact_phone', '').strip() or None
            hr_data.emergency_contact_relation = request.form.get('emergency_contact_relation', '').strip() or None
            
            # Formazione
            hr_data.education_level = request.form.get('education_level', '').strip() or None
            hr_data.education_field = request.form.get('education_field', '').strip() or None
            
            # Altri dati
            hr_data.marital_status = request.form.get('marital_status', '').strip() or None
            
            dependents_str = request.form.get('dependents_number', '').strip()
            if dependents_str:
                hr_data.dependents_number = int(dependents_str)
            
            hr_data.disability = request.form.get('disability') == 'on'
            
            disability_perc_str = request.form.get('disability_percentage', '').strip()
            if disability_perc_str and hr_data.disability:
                hr_data.disability_percentage = int(disability_perc_str)
            
            # Note
            hr_data.notes = request.form.get('notes', '').strip() or None
            
            # Benefit aziendali
            meal_vouchers_str = request.form.get('meal_vouchers_value', '').strip()
            if meal_vouchers_str:
                hr_data.meal_vouchers_value = float(meal_vouchers_str.replace(',', '.'))
            else:
                hr_data.meal_vouchers_value = None
            
            hr_data.fuel_card = request.form.get('fuel_card') == 'on'
            
            # Patente
            hr_data.driver_license_number = request.form.get('driver_license_number', '').strip() or None
            hr_data.driver_license_type = request.form.get('driver_license_type', '').strip() or None
            
            driver_license_expiry_str = request.form.get('driver_license_expiry', '').strip()
            if driver_license_expiry_str:
                hr_data.driver_license_expiry = datetime.strptime(driver_license_expiry_str, '%Y-%m-%d').date()
            else:
                hr_data.driver_license_expiry = None
            
            # Dati operativi - con validazione multi-tenant
            sede_id_str = request.form.get('sede_id', '').strip()
            if sede_id_str:
                sede_id = int(sede_id_str)
                # Verifica che la sede appartenga alla company dell'utente
                sede = filter_by_company(Sede.query).filter_by(id=sede_id).first()
                if sede:
                    hr_data.sede_id = sede_id
                else:
                    flash('Sede non valida per questa azienda', 'warning')
                    hr_data.sede_id = None
            else:
                hr_data.sede_id = None
            
            aci_vehicle_id_str = request.form.get('aci_vehicle_id', '').strip()
            if aci_vehicle_id_str:
                aci_vehicle_id = int(aci_vehicle_id_str)
                # ACI table è globale, non serve validazione multi-tenant
                hr_data.aci_vehicle_id = aci_vehicle_id
            else:
                hr_data.aci_vehicle_id = None
            
            hr_data.banca_ore_enabled = request.form.get('banca_ore_enabled') == 'on'
            
            banca_ore_limite_str = request.form.get('banca_ore_limite_max', '').strip()
            if banca_ore_limite_str:
                hr_data.banca_ore_limite_max = float(banca_ore_limite_str.replace(',', '.'))
            
            banca_ore_periodo_str = request.form.get('banca_ore_periodo_mesi', '').strip()
            if banca_ore_periodo_str:
                hr_data.banca_ore_periodo_mesi = int(banca_ore_periodo_str)
            
            # Requisiti e sicurezza
            hr_data.minimum_requirements = request.form.get('minimum_requirements', '').strip() or None
            
            # Visita medica
            medical_visit_date_str = request.form.get('medical_visit_date', '').strip()
            if medical_visit_date_str:
                hr_data.medical_visit_date = datetime.strptime(medical_visit_date_str, '%Y-%m-%d').date()
            else:
                hr_data.medical_visit_date = None
            
            medical_visit_expiry_str = request.form.get('medical_visit_expiry', '').strip()
            if medical_visit_expiry_str:
                hr_data.medical_visit_expiry = datetime.strptime(medical_visit_expiry_str, '%Y-%m-%d').date()
            else:
                hr_data.medical_visit_expiry = None
            
            # Formazioni
            # Formazione generale
            training_general_date_str = request.form.get('training_general_date', '').strip()
            if training_general_date_str:
                hr_data.training_general_date = datetime.strptime(training_general_date_str, '%Y-%m-%d').date()
            else:
                hr_data.training_general_date = None
            
            training_general_expiry_str = request.form.get('training_general_expiry', '').strip()
            if training_general_expiry_str:
                hr_data.training_general_expiry = datetime.strptime(training_general_expiry_str, '%Y-%m-%d').date()
            else:
                hr_data.training_general_expiry = None
            
            # Formazione RSPP
            training_rspp_date_str = request.form.get('training_rspp_date', '').strip()
            if training_rspp_date_str:
                hr_data.training_rspp_date = datetime.strptime(training_rspp_date_str, '%Y-%m-%d').date()
            else:
                hr_data.training_rspp_date = None
            
            training_rspp_expiry_str = request.form.get('training_rspp_expiry', '').strip()
            if training_rspp_expiry_str:
                hr_data.training_rspp_expiry = datetime.strptime(training_rspp_expiry_str, '%Y-%m-%d').date()
            else:
                hr_data.training_rspp_expiry = None
            
            # Formazione RLS
            training_rls_date_str = request.form.get('training_rls_date', '').strip()
            if training_rls_date_str:
                hr_data.training_rls_date = datetime.strptime(training_rls_date_str, '%Y-%m-%d').date()
            else:
                hr_data.training_rls_date = None
            
            training_rls_expiry_str = request.form.get('training_rls_expiry', '').strip()
            if training_rls_expiry_str:
                hr_data.training_rls_expiry = datetime.strptime(training_rls_expiry_str, '%Y-%m-%d').date()
            else:
                hr_data.training_rls_expiry = None
            
            # Formazione primo soccorso
            training_first_aid_date_str = request.form.get('training_first_aid_date', '').strip()
            if training_first_aid_date_str:
                hr_data.training_first_aid_date = datetime.strptime(training_first_aid_date_str, '%Y-%m-%d').date()
            else:
                hr_data.training_first_aid_date = None
            
            training_first_aid_expiry_str = request.form.get('training_first_aid_expiry', '').strip()
            if training_first_aid_expiry_str:
                hr_data.training_first_aid_expiry = datetime.strptime(training_first_aid_expiry_str, '%Y-%m-%d').date()
            else:
                hr_data.training_first_aid_expiry = None
            
            # Formazione emergenza
            training_emergency_date_str = request.form.get('training_emergency_date', '').strip()
            if training_emergency_date_str:
                hr_data.training_emergency_date = datetime.strptime(training_emergency_date_str, '%Y-%m-%d').date()
            else:
                hr_data.training_emergency_date = None
            
            training_emergency_expiry_str = request.form.get('training_emergency_expiry', '').strip()
            if training_emergency_expiry_str:
                hr_data.training_emergency_expiry = datetime.strptime(training_emergency_expiry_str, '%Y-%m-%d').date()
            else:
                hr_data.training_emergency_expiry = None
            
            # Formazione preposto
            training_supervisor_date_str = request.form.get('training_supervisor_date', '').strip()
            if training_supervisor_date_str:
                hr_data.training_supervisor_date = datetime.strptime(training_supervisor_date_str, '%Y-%m-%d').date()
            else:
                hr_data.training_supervisor_date = None
            
            training_supervisor_expiry_str = request.form.get('training_supervisor_expiry', '').strip()
            if training_supervisor_expiry_str:
                hr_data.training_supervisor_expiry = datetime.strptime(training_supervisor_expiry_str, '%Y-%m-%d').date()
            else:
                hr_data.training_supervisor_expiry = None
            
            hr_data.updated_at = datetime.now()
            db.session.commit()
            
            flash('Dati HR aggiornati con successo', 'success')
            return redirect(url_for('hr.hr_detail', user_id=user.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore nel salvataggio: {str(e)}', 'error')
    
    # Carica lista veicoli ACI per il dropdown
    aci_vehicles = ACITable.query.order_by(ACITable.category, ACITable.vehicle_description).all()
    
    return render_template('hr_detail.html', 
                         user=user, 
                         hr_data=hr_data,
                         can_edit=can_edit,
                         aci_vehicles=aci_vehicles)


@hr_bp.route('/export')
@login_required
@require_hr_permission
def hr_export():
    """Export Excel con dati HR completi"""
    
    if not (current_user.can_view_hr_data() or current_user.can_manage_hr_data()):
        flash('Non hai i permessi per esportare i dati HR', 'error')
        return redirect(url_for('hr.hr_list'))
    
    # Ottieni tutti gli utenti con dati HR
    users = filter_by_company(User.query).filter_by(active=True).order_by(User.last_name, User.first_name).all()
    
    # Crea workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Dati HR"
    
    # Styling
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    
    # Headers - Seguendo struttura file Excel: DATI CONTRATTUALI | ANAGRAFICA | VISITE E FORMAZIONE
    headers = [
        # DATI CONTRATTUALI
        'COD SI', 'Cognome', 'Nome',  'Data Assunzione', 'Data Fine Rapporto',
        'Tipologia Contratto', 'CCNL', 'Mansione', 'Qualifica', 'Livello', 'Orario',
        'Sede di Assunzione', 'Cliente', 'Superminimo/SM Assorbibile', 'Rimborsi/Diarie',
        'Ticket', 'Rischio INAIL', 'Tipo di Assunzione', 'Altro/Note',
        # ANAGRAFICA RISORSA
        'Titolo di Studio', 'Luogo di Nascita', 'Data di Nascita', 'Età', 'Sesso', 'C.F.',
        'Comune di Residenza', 'Indirizzo Residenza', 'Domicilio Alternativo', 'CAP',
        'Recapito Telefonico', 'Fruizione Permessi L. 104/92', 'E-mail Personale', 'E-mail Aziendale',
        'Stato Civile', 'Familiari a Carico', 'Contatto Emergenza', 'Tel. Emergenza',
        'Patente Numero', 'Patente Tipo', 'Patente Scadenza',
        'Veicolo ACI', 'Banca Ore', 'Limite Ore', 'Periodo Mesi',
        # VISITE E FORMAZIONE
        'Possesso Requisiti Minimi',
        'Visita Medica - Data', 'Visita Medica - Scadenza',
        'Formazione Generale - Data', 'Formazione Generale - Scadenza',
        'Formazione RSPP - Data', 'Formazione RSPP - Scadenza',
        'Formazione RLS - Data', 'Formazione RLS - Scadenza',
        'Formazione Primo Soccorso - Data', 'Formazione Primo Soccorso - Scadenza',
        'Formazione Emergenza - Data', 'Formazione Emergenza - Scadenza',
        'Formazione Preposto - Data', 'Formazione Preposto - Scadenza'
    ]
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        cell.border = thin_border
    
    # Dati
    for row_idx, user in enumerate(users, 2):
        hr_data = user.hr_data
        
        row_data = [
            # DATI CONTRATTUALI
            hr_data.matricola if hr_data else '',
            user.last_name,
            user.first_name,
            hr_data.hire_date.strftime('%d/%m/%Y') if hr_data and hr_data.hire_date else '',
            hr_data.contract_end_date.strftime('%d/%m/%Y') if hr_data and hr_data.contract_end_date else '',
            hr_data.contract_type if hr_data else '',
            hr_data.ccnl if hr_data else '',
            hr_data.mansione if hr_data else '',
            hr_data.qualifica if hr_data else '',
            hr_data.ccnl_level if hr_data else '',
            str(hr_data.work_hours_week).replace('.', ',') if hr_data and hr_data.work_hours_week else '',
            hr_data.sede.name if hr_data and hr_data.sede else '',
            hr_data.cliente if hr_data else '',
            str(hr_data.superminimo).replace('.', ',') if hr_data and hr_data.superminimo else '',
            str(hr_data.rimborsi_diarie).replace('.', ',') if hr_data and hr_data.rimborsi_diarie else '',
            'Sì' if hr_data and hr_data.ticket_restaurant else 'No' if hr_data else '',
            hr_data.rischio_inail if hr_data else '',
            hr_data.tipo_assunzione if hr_data else '',
            hr_data.other_notes if hr_data else '',
            # ANAGRAFICA RISORSA
            hr_data.education_level if hr_data else '',
            hr_data.birth_city if hr_data else '',
            hr_data.birth_date.strftime('%d/%m/%Y') if hr_data and hr_data.birth_date else '',
            hr_data.get_age() if hr_data else '',
            hr_data.gender if hr_data else '',
            hr_data.codice_fiscale if hr_data else '',
            hr_data.city if hr_data else '',
            hr_data.address if hr_data else '',
            hr_data.alternative_domicile if hr_data else '',
            hr_data.postal_code if hr_data else '',
            hr_data.phone if hr_data else '',
            'Sì' if hr_data and hr_data.law_104_benefits else 'No' if hr_data else '',
            user.email,
            user.work_email if user.work_email else user.email,
            hr_data.marital_status if hr_data else '',
            hr_data.dependents_number if hr_data and hr_data.dependents_number else '',
            hr_data.emergency_contact_name if hr_data else '',
            hr_data.emergency_contact_phone if hr_data else '',
            hr_data.driver_license_number if hr_data else '',
            hr_data.driver_license_type if hr_data else '',
            hr_data.driver_license_expiry.strftime('%d/%m/%Y') if hr_data and hr_data.driver_license_expiry else '',
            f"{hr_data.aci_vehicle.vehicle_description} - {hr_data.aci_vehicle.category}" if hr_data and hr_data.aci_vehicle else '',
            'Sì' if hr_data and hr_data.banca_ore_enabled else 'No' if hr_data else '',
            str(hr_data.banca_ore_limite_max).replace('.', ',') if hr_data and hr_data.banca_ore_limite_max else '',
            str(hr_data.banca_ore_periodo_mesi) if hr_data and hr_data.banca_ore_periodo_mesi else '',
            # VISITE E FORMAZIONE
            hr_data.minimum_requirements if hr_data else '',
            hr_data.medical_visit_date.strftime('%d/%m/%Y') if hr_data and hr_data.medical_visit_date else '',
            hr_data.medical_visit_expiry.strftime('%d/%m/%Y') if hr_data and hr_data.medical_visit_expiry else '',
            hr_data.training_general_date.strftime('%d/%m/%Y') if hr_data and hr_data.training_general_date else '',
            hr_data.training_general_expiry.strftime('%d/%m/%Y') if hr_data and hr_data.training_general_expiry else '',
            hr_data.training_rspp_date.strftime('%d/%m/%Y') if hr_data and hr_data.training_rspp_date else '',
            hr_data.training_rspp_expiry.strftime('%d/%m/%Y') if hr_data and hr_data.training_rspp_expiry else '',
            hr_data.training_rls_date.strftime('%d/%m/%Y') if hr_data and hr_data.training_rls_date else '',
            hr_data.training_rls_expiry.strftime('%d/%m/%Y') if hr_data and hr_data.training_rls_expiry else '',
            hr_data.training_first_aid_date.strftime('%d/%m/%Y') if hr_data and hr_data.training_first_aid_date else '',
            hr_data.training_first_aid_expiry.strftime('%d/%m/%Y') if hr_data and hr_data.training_first_aid_expiry else '',
            hr_data.training_emergency_date.strftime('%d/%m/%Y') if hr_data and hr_data.training_emergency_date else '',
            hr_data.training_emergency_expiry.strftime('%d/%m/%Y') if hr_data and hr_data.training_emergency_expiry else '',
            hr_data.training_supervisor_date.strftime('%d/%m/%Y') if hr_data and hr_data.training_supervisor_date else '',
            hr_data.training_supervisor_expiry.strftime('%d/%m/%Y') if hr_data and hr_data.training_supervisor_expiry else ''
        ]
        
        for col, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col, value=value)
            cell.border = thin_border
    
    # Auto-adjust column widths
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    # Save to BytesIO
    excel_file = BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)
    
    # Generate response
    response = make_response(excel_file.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=dati_hr_{date.today().strftime('%Y%m%d')}.xlsx"
    response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    
    return response
