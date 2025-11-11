"""
Utility per il calcolo del codice fiscale italiano
"""
from datetime import date
from typing import Optional


# Dizionario codici catastali comuni italiani (principali)
COMUNI_CATASTALI = {
    'ROMA': 'H501',
    'MILANO': 'F205',
    'NAPOLI': 'F839',
    'TORINO': 'L219',
    'PALERMO': 'G273',
    'GENOVA': 'D969',
    'BOLOGNA': 'A944',
    'FIRENZE': 'D612',
    'BARI': 'A662',
    'CATANIA': 'C351',
    'VENEZIA': 'L736',
    'VERONA': 'L781',
    'MESSINA': 'F158',
    'PADOVA': 'G224',
    'TRIESTE': 'L424',
    'BRESCIA': 'B157',
    'PRATO': 'G999',
    'TARANTO': 'L049',
    'PARMA': 'G337',
    'REGGIO CALABRIA': 'H224',
    'MODENA': 'F257',
    'REGGIO EMILIA': 'H223',
    'PERUGIA': 'G478',
    'RAVENNA': 'H199',
    'LIVORNO': 'E625',
    'CAGLIARI': 'B354',
    'FOGGIA': 'D643',
    'RIMINI': 'H294',
    'SALERNO': 'H703',
    'FERRARA': 'D548',
    'SASSARI': 'I452',
    'LATINA': 'E472',
    'GIUGLIANO IN CAMPANIA': 'E054',
    'MONZA': 'F704',
    'SIRACUSA': 'I754',
    'PESCARA': 'G482',
    'BERGAMO': 'A794',
    'TRENTO': 'L378',
    'FORLÌ': 'D704',
    'VICENZA': 'L840',
    'TERNI': 'L117',
    'BOLZANO': 'A952',
    'NOVARA': 'F952',
    'PIACENZA': 'G535',
    'ANCONA': 'A271',
    'ANDRIA': 'A285',
    'AREZZO': 'A390',
    'UDINE': 'L483',
    'CESENA': 'C573',
    'LECCE': 'E506',
    'PESARO': 'G479',
    'BARLETTA': 'A669',
    'ALESSANDRIA': 'A182',
    'LA SPEZIA': 'E463',
    'PISA': 'G702',
    'CATANZARO': 'C352',
    'PISTOIA': 'G713',
    'LUCCA': 'E715',
    'BRINDISI': 'B180',
    'COMO': 'C933',
    'TREVISO': 'L407',
    'VARESE': 'L682',
    'MARSALA': 'E974',
    'GROSSETO': 'E202',
    'ASTI': 'A479',
    'CASERTA': 'B963',
    'CREMONA': 'D150',
    'RAGUSA': 'H163',
    'PAVIA': 'G388',
    'TRAPANI': 'L331',
    'SAVONA': 'I480',
    'PORDENONE': 'G888',
    'BENEVENTO': 'A783',
    'GORIZIA': 'E098',
    'SIENA': 'I726',
    'TRANI': 'L328',
    'VITERBO': 'M082',
    'CUNEO': 'D205',
    'LODI': 'E648',
    'CHIETI': 'C632',
    'CROTONE': 'D122',
    'LECCO': 'E507',
    'VERCELLI': 'L750',
    'SONDRIO': 'I829',
    'RIETI': 'H282',
    'IMPERIA': 'E290',
    'ENNA': 'C342',
    'BIELLA': 'A859',
    'VERBANIA': 'L746',
    'ROVIGO': 'H620',
    'BELLUNO': 'A757',
    'MATERA': 'F052',
    'MANTOVA': 'E897',
    'AVELLINO': 'A509',
    'POTENZA': 'G942',
    'TERAMO': 'L103',
    'COSENZA': 'D086',
    'AGRIGENTO': 'A089',
    'L\'AQUILA': 'A345',
    'MASSA': 'F023',
    'CARRARA': 'B832',
    'ASCOLI PICENO': 'A462',
    'FERMO': 'D542',
    'VIBO VALENTIA': 'F537',
    'ISERNIA': 'E335',
    'CAMPOBASSO': 'B519',
    'ORISTANO': 'G113',
    'NUORO': 'F979',
    'AOSTA': 'A326',
}

# Codici catastali per nazioni estere (per cittadini nati all'estero)
PAESI_ESTERI_CATASTALI = {
    'AFGHANISTAN': 'Z200',
    'ALBANIA': 'Z100',
    'ALGERIA': 'Z301',
    'ANDORRA': 'Z101',
    'ANGOLA': 'Z302',
    'ANTIGUA E BARBUDA': 'Z532',
    'ARABIA SAUDITA': 'Z203',
    'ARGENTINA': 'Z600',
    'ARMENIA': 'Z252',
    'AUSTRALIA': 'Z700',
    'AUSTRIA': 'Z102',
    'AZERBAIGIAN': 'Z253',
    'BAHAMAS': 'Z533',
    'BAHREIN': 'Z204',
    'BANGLADESH': 'Z249',
    'BARBADOS': 'Z534',
    'BELGIO': 'Z103',
    'BELIZE': 'Z524',
    'BENIN': 'Z314',
    'BIELORUSSIA': 'Z139',
    'BIRMANIA': 'Z241',
    'BOLIVIA': 'Z601',
    'BOSNIA ED ERZEGOVINA': 'Z153',
    'BOTSWANA': 'Z358',
    'BRASILE': 'Z602',
    'BRUNEI': 'Z272',
    'BULGARIA': 'Z104',
    'BURKINA FASO': 'Z354',
    'BURUNDI': 'Z305',
    'CAMBOGIA': 'Z247',
    'CAMERUN': 'Z306',
    'CANADA': 'Z401',
    'CAPO VERDE': 'Z347',
    'CIAD': 'Z309',
    'CILE': 'Z603',
    'CINA': 'Z210',
    'CIPRO': 'Z211',
    'CITTA DEL VATICANO': 'Z106',
    'COLOMBIA': 'Z604',
    'COMORE': 'Z318',
    'CONGO': 'Z312',
    'COREA DEL NORD': 'Z214',
    'COREA DEL SUD': 'Z213',
    'COSTA D\'AVORIO': 'Z313',
    'COSTA RICA': 'Z503',
    'CROAZIA': 'Z149',
    'CUBA': 'Z504',
    'DANIMARCA': 'Z107',
    'DOMINICA': 'Z540',
    'ECUADOR': 'Z605',
    'EGITTO': 'Z336',
    'EL SALVADOR': 'Z506',
    'EMIRATI ARABI UNITI': 'Z215',
    'ERITREA': 'Z368',
    'ESTONIA': 'Z144',
    'ETIOPIA': 'Z315',
    'FIJI': 'Z705',
    'FILIPPINE': 'Z216',
    'FINLANDIA': 'Z108',
    'FRANCIA': 'Z110',
    'GABON': 'Z316',
    'GAMBIA': 'Z320',
    'GEORGIA': 'Z254',
    'GERMANIA': 'Z112',
    'GHANA': 'Z319',
    'GIAMAICA': 'Z507',
    'GIAPPONE': 'Z219',
    'GIBUTI': 'Z361',
    'GIORDANIA': 'Z220',
    'GRECIA': 'Z115',
    'GRENADA': 'Z545',
    'GUATEMALA': 'Z508',
    'GUINEA': 'Z323',
    'GUINEA EQUATORIALE': 'Z325',
    'GUINEA-BISSAU': 'Z359',
    'GUYANA': 'Z607',
    'HAITI': 'Z509',
    'HONDURAS': 'Z510',
    'INDIA': 'Z222',
    'INDONESIA': 'Z223',
    'IRAN': 'Z224',
    'IRAQ': 'Z225',
    'IRLANDA': 'Z116',
    'ISLANDA': 'Z117',
    'ISRAELE': 'Z226',
    'KAZAKISTAN': 'Z255',
    'KENYA': 'Z326',
    'KIRGHIZISTAN': 'Z256',
    'KIRIBATI': 'Z712',
    'KUWAIT': 'Z227',
    'LAOS': 'Z234',
    'LESOTHO': 'Z360',
    'LETTONIA': 'Z145',
    'LIBANO': 'Z229',
    'LIBERIA': 'Z328',
    'LIBIA': 'Z330',
    'LIECHTENSTEIN': 'Z118',
    'LITUANIA': 'Z146',
    'LUSSEMBURGO': 'Z119',
    'MACEDONIA DEL NORD': 'Z154',
    'MADAGASCAR': 'Z317',
    'MALAWI': 'Z338',
    'MALAYSIA': 'Z247',
    'MALDIVE': 'Z235',
    'MALI': 'Z329',
    'MALTA': 'Z121',
    'MAROCCO': 'Z330',
    'MAURITANIA': 'Z332',
    'MAURITIUS': 'Z370',
    'MESSICO': 'Z514',
    'MICRONESIA': 'Z713',
    'MOLDAVIA': 'Z140',
    'MONACO': 'Z123',
    'MONGOLIA': 'Z239',
    'MONTENEGRO': 'Z157',
    'MOZAMBICO': 'Z343',
    'NAMIBIA': 'Z369',
    'NEPAL': 'Z240',
    'NICARAGUA': 'Z515',
    'NIGER': 'Z335',
    'NIGERIA': 'Z334',
    'NORVEGIA': 'Z125',
    'NUOVA ZELANDA': 'Z719',
    'OMAN': 'Z242',
    'PAESI BASSI': 'Z126',
    'PAKISTAN': 'Z243',
    'PANAMA': 'Z516',
    'PAPUA NUOVA GUINEA': 'Z720',
    'PARAGUAY': 'Z608',
    'PERU': 'Z611',
    'POLONIA': 'Z127',
    'PORTOGALLO': 'Z128',
    'QATAR': 'Z245',
    'REGNO UNITO': 'Z114',
    'REPUBBLICA CECA': 'Z156',
    'REPUBBLICA CENTRAFRICANA': 'Z308',
    'REPUBBLICA DEMOCRATICA DEL CONGO': 'Z311',
    'REPUBBLICA DOMINICANA': 'Z505',
    'ROMANIA': 'Z129',
    'RUANDA': 'Z338',
    'RUSSIA': 'Z130',
    'SAINT KITTS E NEVIS': 'Z549',
    'SAINT LUCIA': 'Z550',
    'SAINT VINCENT E GRENADINE': 'Z551',
    'SAMOA': 'Z721',
    'SAN MARINO': 'Z133',
    'SENEGAL': 'Z341',
    'SERBIA': 'Z158',
    'SEYCHELLES': 'Z371',
    'SIERRA LEONE': 'Z342',
    'SINGAPORE': 'Z248',
    'SIRIA': 'Z249',
    'SLOVACCHIA': 'Z155',
    'SLOVENIA': 'Z150',
    'SOMALIA': 'Z345',
    'SPAGNA': 'Z131',
    'SRI LANKA': 'Z209',
    'STATI UNITI': 'Z404',
    'SUD AFRICA': 'Z357',
    'SUDAN': 'Z346',
    'SUDAN DEL SUD': 'Z372',
    'SURINAME': 'Z617',
    'SVEZIA': 'Z132',
    'SVIZZERA': 'Z133',
    'TAGIKISTAN': 'Z259',
    'TANZANIA': 'Z357',
    'THAILANDIA': 'Z250',
    'TIMOR EST': 'Z280',
    'TOGO': 'Z351',
    'TONGA': 'Z725',
    'TRINIDAD E TOBAGO': 'Z552',
    'TUNISIA': 'Z352',
    'TURCHIA': 'Z134',
    'TURKMENISTAN': 'Z260',
    'UCRAINA': 'Z138',
    'UGANDA': 'Z353',
    'UNGHERIA': 'Z135',
    'URUGUAY': 'Z613',
    'UZBEKISTAN': 'Z261',
    'VANUATU': 'Z726',
    'VENEZUELA': 'Z614',
    'VIETNAM': 'Z251',
    'YEMEN': 'Z258',
    'ZAMBIA': 'Z355',
    'ZIMBABWE': 'Z356',
}


def get_codice_catastale(city_name: Optional[str], country: Optional[str] = None) -> str:
    """
    Ottiene il codice catastale di un comune italiano o di una nazione estera
    
    Args:
        city_name: Nome del comune (se Italia)
        country: Nome della nazione (per verificare se estero)
        
    Returns:
        Codice catastale (4 caratteri) o Z000 se non trovato
    """
    # Se la nazione è specificata e NON è Italia, usa il codice paese
    if country:
        country_normalized = ' '.join(country.upper().strip().split())
        if country_normalized != 'ITALIA' and country_normalized != 'ITALY':
            # Per nazioni estere, usa il codice paese
            return PAESI_ESTERI_CATASTALI.get(country_normalized, 'Z000')
    
    # Se è Italia o nazione non specificata, cerca il comune
    if not city_name:
        return 'Z000'
    
    # Normalizza il nome (uppercase, rimuovi spazi multipli)
    city_normalized = ' '.join(city_name.upper().strip().split())
    
    return COMUNI_CATASTALI.get(city_normalized, 'Z000')


# Tabella conversione mesi
MONTH_CODES = {
    1: 'A', 2: 'B', 3: 'C', 4: 'D', 5: 'E', 6: 'H',
    7: 'L', 8: 'M', 9: 'P', 10: 'R', 11: 'S', 12: 'T'
}

# Tabella per il calcolo del carattere di controllo
ODD_VALUES = {
    '0': 1, '1': 0, '2': 5, '3': 7, '4': 9, '5': 13, '6': 15, '7': 17, '8': 19, '9': 21,
    'A': 1, 'B': 0, 'C': 5, 'D': 7, 'E': 9, 'F': 13, 'G': 15, 'H': 17, 'I': 19, 'J': 21,
    'K': 2, 'L': 4, 'M': 18, 'N': 20, 'O': 11, 'P': 3, 'Q': 6, 'R': 8, 'S': 12, 'T': 14,
    'U': 16, 'V': 10, 'W': 22, 'X': 25, 'Y': 24, 'Z': 23
}

EVEN_VALUES = {
    '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
    'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9,
    'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18,
    'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25
}

CHECK_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'


def extract_consonants(s: str) -> str:
    """Estrae le consonanti da una stringa"""
    vowels = 'AEIOU'
    return ''.join(c for c in s.upper() if c.isalpha() and c not in vowels)


def extract_vowels(s: str) -> str:
    """Estrae le vocali da una stringa"""
    vowels = 'AEIOU'
    return ''.join(c for c in s.upper() if c in vowels)


def encode_surname(surname: str) -> str:
    """Codifica il cognome per il codice fiscale"""
    consonants = extract_consonants(surname)
    vowels = extract_vowels(surname)
    
    code = consonants + vowels + 'XXX'
    return code[:3]


def encode_name(name: str) -> str:
    """Codifica il nome per il codice fiscale"""
    consonants = extract_consonants(name)
    vowels = extract_vowels(name)
    
    if len(consonants) > 3:
        code = consonants[0] + consonants[2] + consonants[3]
    else:
        code = consonants + vowels + 'XXX'
    
    return code[:3]


def encode_birth_date(birth_date: date, gender: str) -> str:
    """Codifica data di nascita e sesso"""
    year = str(birth_date.year)[-2:]
    month = MONTH_CODES[birth_date.month]
    day = birth_date.day
    
    if gender and gender.upper() == 'F':
        day += 40
    
    return f"{year}{month}{day:02d}"


def calculate_check_char(code: str) -> str:
    """Calcola il carattere di controllo"""
    total = 0
    
    for i, char in enumerate(code):
        if i % 2 == 0:
            total += ODD_VALUES.get(char, 0)
        else:
            total += EVEN_VALUES.get(char, 0)
    
    return CHECK_CHARS[total % 26]


def calculate_codice_fiscale(
    first_name: Optional[str],
    last_name: Optional[str],
    birth_date: Optional[date],
    gender: Optional[str],
    birth_city: Optional[str] = None,
    birth_country: Optional[str] = None
) -> Optional[str]:
    """
    Calcola il codice fiscale italiano
    
    Args:
        first_name: Nome
        last_name: Cognome
        birth_date: Data di nascita
        gender: Sesso ('M' o 'F')
        birth_city: Nome del comune di nascita (es. 'Roma', 'Milano')
        birth_country: Nome della nazione di nascita (es. 'Italia', 'Francia')
        
    Returns:
        Codice fiscale o None se i dati sono insufficienti
    """
    if not all([first_name, last_name, birth_date, gender]):
        return None
    
    try:
        surname_code = encode_surname(last_name)
        name_code = encode_name(first_name)
        birth_code = encode_birth_date(birth_date, gender)
        
        # Ottieni il codice catastale (comune italiano o paese estero)
        city_code = get_codice_catastale(birth_city, birth_country)
        
        partial_code = surname_code + name_code + birth_code + city_code
        check_char = calculate_check_char(partial_code)
        
        return (partial_code + check_char).upper()
    except Exception:
        return None
