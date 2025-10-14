"""
Utility per sicurezza: sanitizzazione HTML, validazione file upload
"""
import bleach
import os
from werkzeug.utils import secure_filename

# Configurazione sanitizzazione HTML
ALLOWED_HTML_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li', 
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'blockquote', 'code', 'pre', 'hr', 'div', 'span'
]

ALLOWED_HTML_ATTRIBUTES = {
    'a': ['href', 'title', 'target'],
    'img': ['src', 'alt', 'title'],
    '*': ['class']
}

ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']

# Configurazione file upload
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'odt', 'ods'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB


def sanitize_html(dirty_html):
    """
    Sanitizza HTML rimuovendo tag e attributi potenzialmente pericolosi.
    
    Args:
        dirty_html (str): HTML non sicuro da sanitizzare
        
    Returns:
        str: HTML sanitizzato e sicuro
    """
    if not dirty_html:
        return ''
    
    # Sanitizza HTML con bleach
    clean_html = bleach.clean(
        dirty_html,
        tags=ALLOWED_HTML_TAGS,
        attributes=ALLOWED_HTML_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True  # Rimuove tag non consentiti invece di escaparli
    )
    
    # Linkify automaticamente gli URL nel testo
    clean_html = bleach.linkify(clean_html)
    
    return clean_html


def allowed_file(filename, allowed_extensions=None):
    """
    Verifica se un file ha un'estensione consentita.
    
    Args:
        filename (str): Nome del file da verificare
        allowed_extensions (set): Set di estensioni consentite (default: immagini)
        
    Returns:
        bool: True se l'estensione è consentita
    """
    if allowed_extensions is None:
        allowed_extensions = ALLOWED_IMAGE_EXTENSIONS
    
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def validate_file_size(file_storage, max_size=None):
    """
    Verifica la dimensione di un file.
    
    Args:
        file_storage: FileStorage object di werkzeug
        max_size (int): Dimensione massima in bytes (default: MAX_FILE_SIZE)
        
    Returns:
        tuple: (bool, str) - (valido, messaggio_errore)
    """
    if max_size is None:
        max_size = MAX_FILE_SIZE
    
    # Salva posizione corrente
    file_storage.seek(0, os.SEEK_END)
    file_size = file_storage.tell()
    file_storage.seek(0)  # Reset position
    
    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        return False, f"Il file è troppo grande. Dimensione massima: {max_mb:.1f}MB"
    
    return True, ""


def validate_image_upload(file_storage):
    """
    Valida un'immagine caricata.
    
    Args:
        file_storage: FileStorage object di werkzeug
        
    Returns:
        tuple: (bool, str) - (valido, messaggio_errore)
    """
    if not file_storage:
        return False, "Nessun file selezionato"
    
    if file_storage.filename == '':
        return False, "Nessun file selezionato"
    
    # Verifica estensione
    if not allowed_file(file_storage.filename, ALLOWED_IMAGE_EXTENSIONS):
        return False, f"Formato file non consentito. Usa: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
    
    # Verifica dimensione
    valid_size, error_msg = validate_file_size(file_storage, MAX_IMAGE_SIZE)
    if not valid_size:
        return False, error_msg
    
    return True, ""


def validate_document_upload(file_storage):
    """
    Valida un documento caricato.
    
    Args:
        file_storage: FileStorage object di werkzeug
        
    Returns:
        tuple: (bool, str) - (valido, messaggio_errore)
    """
    if not file_storage:
        return False, "Nessun file selezionato"
    
    if file_storage.filename == '':
        return False, "Nessun file selezionato"
    
    # Verifica estensione
    if not allowed_file(file_storage.filename, ALLOWED_DOCUMENT_EXTENSIONS):
        return False, f"Formato file non consentito. Usa: {', '.join(ALLOWED_DOCUMENT_EXTENSIONS)}"
    
    # Verifica dimensione
    valid_size, error_msg = validate_file_size(file_storage, MAX_FILE_SIZE)
    if not valid_size:
        return False, error_msg
    
    return True, ""


def get_safe_filename(filename):
    """
    Ottiene un nome file sicuro.
    
    Args:
        filename (str): Nome file originale
        
    Returns:
        str: Nome file sicuro
    """
    return secure_filename(filename)
