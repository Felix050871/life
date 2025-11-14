"""
Central constants file for the Life Platform
Defines all system-wide constants to avoid hardcoded values
"""

# =============================================================================
# USER ROLES
# =============================================================================
class RoleNames:
    """User role name constants"""
    SUPERADMIN = 'SUPERADMIN'
    ADMIN = 'ADMIN'
    HR = 'HR'
    MANAGER = 'MANAGER'
    USER = 'USER'
    
    @classmethod
    def all(cls):
        """Return all roles"""
        return [cls.SUPERADMIN, cls.ADMIN, cls.HR, cls.MANAGER, cls.USER]
    
    @classmethod
    def is_valid(cls, role):
        """Check if role is valid"""
        return role in cls.all()


# =============================================================================
# REQUEST STATUS
# =============================================================================
class RequestStatus:
    """Status constants for various request types"""
    PENDING = 'Pending'
    APPROVED = 'Approved'
    REJECTED = 'Rejected'
    CANCELLED = 'Cancelled'
    
    @classmethod
    def all(cls):
        """Return all statuses"""
        return [cls.PENDING, cls.APPROVED, cls.REJECTED, cls.CANCELLED]


# =============================================================================
# TIMESHEET STATUS
# =============================================================================
class TimesheetStatus:
    """Timesheet consolidation and validation status"""
    NOT_CONSOLIDATED = 'not_consolidated'
    CONSOLIDATED = 'consolidated'
    VALIDATED = 'validated'
    REJECTED = 'rejected'
    
    @classmethod
    def all_consolidation(cls):
        """Return consolidation statuses"""
        return [cls.NOT_CONSOLIDATED, cls.CONSOLIDATED]
    
    @classmethod
    def all_validation(cls):
        """Return validation statuses"""
        return [cls.CONSOLIDATED, cls.VALIDATED, cls.REJECTED]


# =============================================================================
# ATTENDANCE EVENT TYPES
# =============================================================================
class AttendanceEventType:
    """Attendance event type constants"""
    CLOCK_IN = 'clock_in'
    CLOCK_OUT = 'clock_out'
    BREAK_START = 'break_start'
    BREAK_END = 'break_end'
    
    @classmethod
    def all(cls):
        """Return all event types"""
        return [cls.CLOCK_IN, cls.CLOCK_OUT, cls.BREAK_START, cls.BREAK_END]


# =============================================================================
# OVERTIME TYPES
# =============================================================================
class OvertimeTypes:
    """Overtime type name constants"""
    PAID = 'Straordinario Pagato'
    TIME_BANK = 'Banca Ore'
    
    @classmethod
    def all(cls):
        """Return all overtime types"""
        return [cls.PAID, cls.TIME_BANK]


# =============================================================================
# CIRCLE POST TYPES
# =============================================================================
class CirclePostType:
    """Circle post type constants"""
    NEWS = 'news'
    ANNOUNCEMENT = 'announcement'
    GENERAL = 'general'
    
    @classmethod
    def all(cls):
        """Return all post types"""
        return [cls.NEWS, cls.ANNOUNCEMENT, cls.GENERAL]


# =============================================================================
# GROUP MEMBERSHIP STATUS
# =============================================================================
class GroupMembershipStatus:
    """Circle group membership request status"""
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    
    @classmethod
    def all(cls):
        """Return all statuses"""
        return [cls.PENDING, cls.APPROVED, cls.REJECTED]


# =============================================================================
# PRIORITY LEVELS
# =============================================================================
class PriorityLevel:
    """Priority level constants"""
    LOW = 'bassa'
    MEDIUM = 'media'
    HIGH = 'alta'
    URGENT = 'urgente'
    
    @classmethod
    def all(cls):
        """Return all priority levels"""
        return [cls.LOW, cls.MEDIUM, cls.HIGH, cls.URGENT]


# =============================================================================
# DEFAULT CONFIGURATIONS
# =============================================================================
class DefaultConfig:
    """Default configuration values"""
    # Password requirements
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGIT = True
    PASSWORD_REQUIRE_SPECIAL = True
    
    # Session configuration
    SESSION_TIMEOUT_HOURS = 24
    PASSWORD_RESET_TOKEN_HOURS = 1
    
    # File upload limits
    MAX_PROFILE_IMAGE_SIZE_MB = 5
    MAX_DOCUMENT_SIZE_MB = 10
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt'}
    
    # Pagination
    ITEMS_PER_PAGE = 20
    MAX_ITEMS_PER_PAGE = 100
    
    # Default leave types (for seeding)
    DEFAULT_LEAVE_FERIE_HOURS = 8
    DEFAULT_LEAVE_MALATTIA_HOURS = 4
    
    # Timesheet defaults
    TIMESHEET_HOURS_PER_DAY = 8
    TIMESHEET_WORK_DAYS_PER_WEEK = 5
    
    # Mileage reimbursement
    DEFAULT_MILEAGE_RATE_EUR_KM = 0.50


# =============================================================================
# VALIDATION MESSAGES
# =============================================================================
class ValidationMessage:
    """Validation error messages"""
    REQUIRED_FIELD = 'Questo campo è obbligatorio'
    INVALID_EMAIL = 'Indirizzo email non valido'
    INVALID_DATE = 'Data non valida'
    INVALID_TIME = 'Orario non valido'
    PASSWORD_TOO_SHORT = f'La password deve contenere almeno {DefaultConfig.PASSWORD_MIN_LENGTH} caratteri'
    PASSWORD_REQUIREMENTS = 'La password deve contenere almeno una lettera maiuscola, una minuscola, un numero e un carattere speciale'
    USERNAME_TAKEN = 'Username già in uso'
    EMAIL_TAKEN = 'Email già in uso'
    INVALID_CREDENTIALS = 'Credenziali non valide'
    PERMISSION_DENIED = 'Non hai i permessi per questa operazione'
    TENANT_REQUIRED = 'Contesto tenant non valido'


# =============================================================================
# SUCCESS MESSAGES
# =============================================================================
class SuccessMessage:
    """Success messages"""
    LOGIN_SUCCESS = 'Accesso effettuato con successo'
    LOGOUT_SUCCESS = 'Disconnessione effettuata con successo'
    PASSWORD_CHANGED = 'Password cambiata con successo'
    PASSWORD_RESET_SENT = 'Se l\'email esiste nel sistema, riceverai un link per il reset della password'
    PASSWORD_RESET_SUCCESS = 'Password reimpostata con successo. Puoi ora accedere con la nuova password'
    DATA_SAVED = 'Dati salvati con successo'
    DATA_DELETED = 'Dati eliminati con successo'
    REQUEST_SUBMITTED = 'Richiesta inviata con successo'
    REQUEST_APPROVED = 'Richiesta approvata con successo'
    REQUEST_REJECTED = 'Richiesta rifiutata con successo'


# =============================================================================
# ERROR MESSAGES
# =============================================================================
class ErrorMessage:
    """Error messages"""
    GENERIC_ERROR = 'Si è verificato un errore. Riprova più tardi'
    DATABASE_ERROR = 'Errore del database. Contatta l\'amministratore'
    UNAUTHORIZED = 'Non autorizzato'
    NOT_FOUND = 'Risorsa non trovata'
    INVALID_TOKEN = 'Token non valido o scaduto'
    FILE_TOO_LARGE = 'File troppo grande'
    INVALID_FILE_TYPE = 'Tipo di file non valido'
    DUPLICATE_ENTRY = 'Voce duplicata'
    INVALID_DATE_RANGE = 'Intervallo di date non valido'
