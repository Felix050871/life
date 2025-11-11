"""
Utility per il calcolo del codice fiscale italiano
"""
from datetime import date
from typing import Optional


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
    birth_city_code: Optional[str] = None
) -> Optional[str]:
    """
    Calcola il codice fiscale italiano
    
    Args:
        first_name: Nome
        last_name: Cognome
        birth_date: Data di nascita
        gender: Sesso ('M' o 'F')
        birth_city_code: Codice catastale del comune (4 caratteri)
        
    Returns:
        Codice fiscale o None se i dati sono insufficienti
    """
    if not all([first_name, last_name, birth_date, gender]):
        return None
    
    try:
        surname_code = encode_surname(last_name)
        name_code = encode_name(first_name)
        birth_code = encode_birth_date(birth_date, gender)
        
        city_code = (birth_city_code or 'Z000').upper()[:4].ljust(4, 'X')
        
        partial_code = surname_code + name_code + birth_code + city_code
        check_char = calculate_check_char(partial_code)
        
        return (partial_code + check_char).upper()
    except Exception:
        return None
