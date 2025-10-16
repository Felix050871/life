"""
Utility per encryption/decryption di dati sensibili
Usa Fernet (symmetric encryption) per criptare password SMTP e altri secrets
"""

import os
from cryptography.fernet import Fernet
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

def get_encryption_key():
    """
    Ottiene la chiave di encryption dalle variabili ambiente.
    Se non esiste, genera una nuova chiave (solo per development).
    
    IMPORTANTE: In produzione, ENCRYPTION_KEY deve essere impostato nelle variabili ambiente!
    """
    encryption_key = os.environ.get('ENCRYPTION_KEY')
    
    if not encryption_key:
        # In development, usa SECRET_KEY per derivare una chiave
        # In produzione, usa una chiave dedicata
        secret = os.environ.get('SESSION_SECRET', 'dev-secret-key-please-change-in-production')
        
        # Deriva una chiave Fernet valida dal secret usando PBKDF2
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'life-platform-salt',  # Salt fisso per consistency
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
        return key
    
    return encryption_key.encode()


def encrypt_value(plain_text):
    """
    Cripta un valore in chiaro
    
    Args:
        plain_text: Stringa da criptare
        
    Returns:
        Stringa criptata (base64)
    """
    if not plain_text:
        return None
        
    key = get_encryption_key()
    f = Fernet(key)
    encrypted = f.encrypt(plain_text.encode())
    return encrypted.decode()


def decrypt_value(encrypted_text):
    """
    Decripta un valore criptato
    
    Args:
        encrypted_text: Stringa criptata (base64)
        
    Returns:
        Stringa in chiaro
    """
    if not encrypted_text:
        return None
        
    key = get_encryption_key()
    f = Fernet(key)
    
    try:
        decrypted = f.decrypt(encrypted_text.encode())
        return decrypted.decode()
    except Exception as e:
        print(f"Errore decryption: {str(e)}")
        return None


def generate_encryption_key():
    """
    Genera una nuova chiave di encryption Fernet.
    Usare questo metodo per generare ENCRYPTION_KEY da impostare nelle variabili ambiente.
    
    Returns:
        Chiave Fernet come stringa base64
    """
    key = Fernet.generate_key()
    return key.decode()
