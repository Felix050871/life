#!/bin/bash
# Workly - Backup Script

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/var/backups/workly}"
APP_DIR="${APP_DIR:-/home/workly/app}"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Load environment variables
if [[ -f "$APP_DIR/.env" ]]; then
    source "$APP_DIR/.env"
else
    error ".env file not found in $APP_DIR"
fi

# Parse DATABASE_URL
if [[ -z "$DATABASE_URL" ]]; then
    error "DATABASE_URL not set"
fi

# Extract database connection details
DB_HOST=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
DB_PORT=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
DB_NAME=$(echo "$DATABASE_URL" | sed -n 's/.*\/\([^?]*\).*/\1/p')
DB_USER=$(echo "$DATABASE_URL" | sed -n 's/.*\/\/\([^:]*\):.*/\1/p')
DB_PASS=$(echo "$DATABASE_URL" | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')

# Set defaults
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}

log "Starting backup process..."

# Database backup
backup_database() {
    log "Backing up database..."
    
    export PGPASSWORD="$DB_PASS"
    
    # Full database backup
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" | \
        gzip > "$BACKUP_DIR/database_$DATE.sql.gz"
    
    # Schema-only backup
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" --schema-only | \
        gzip > "$BACKUP_DIR/schema_$DATE.sql.gz"
    
    unset PGPASSWORD
    
    log "Database backup completed: database_$DATE.sql.gz"
}

# Application files backup
backup_application() {
    log "Backing up application files..."
    
    tar -czf "$BACKUP_DIR/application_$DATE.tar.gz" \
        -C "$(dirname "$APP_DIR")" \
        --exclude=venv \
        --exclude=__pycache__ \
        --exclude=.git \
        --exclude=*.pyc \
        --exclude=logs \
        --exclude=instance/uploads \
        "$(basename "$APP_DIR")"
    
    log "Application backup completed: application_$DATE.tar.gz"
}

# Configuration backup
backup_config() {
    log "Backing up configuration..."
    
    mkdir -p "$BACKUP_DIR/config_$DATE"
    
    # Copy important config files
    [[ -f "$APP_DIR/.env" ]] && cp "$APP_DIR/.env" "$BACKUP_DIR/config_$DATE/"
    [[ -f "/etc/systemd/system/workly.service" ]] && sudo cp "/etc/systemd/system/workly.service" "$BACKUP_DIR/config_$DATE/" 2>/dev/null || true
    [[ -f "/etc/nginx/sites-available/workly" ]] && sudo cp "/etc/nginx/sites-available/workly" "$BACKUP_DIR/config_$DATE/" 2>/dev/null || true
    
    tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" -C "$BACKUP_DIR" "config_$DATE"
    rm -rf "$BACKUP_DIR/config_$DATE"
    
    log "Configuration backup completed: config_$DATE.tar.gz"
}

# Cleanup old backups
cleanup_old_backups() {
    log "Cleaning up old backups (older than $RETENTION_DAYS days)..."
    
    find "$BACKUP_DIR" -name "database_*.sql.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
    find "$BACKUP_DIR" -name "schema_*.sql.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
    find "$BACKUP_DIR" -name "application_*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
    find "$BACKUP_DIR" -name "config_*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
    
    log "Cleanup completed"
}

# Create backup manifest
create_manifest() {
    log "Creating backup manifest..."
    
    cat > "$BACKUP_DIR/manifest_$DATE.txt" << EOF
Workly Backup Manifest
Generated: $(date)
Hostname: $(hostname)
Backup Directory: $BACKUP_DIR

Files:
$(ls -la "$BACKUP_DIR"/*_$DATE.* 2>/dev/null || echo "No files found")

Database Info:
Host: $DB_HOST
Port: $DB_PORT  
Database: $DB_NAME
User: $DB_USER

Application:
Directory: $APP_DIR
Version: $(git -C "$APP_DIR" describe --tags 2>/dev/null || echo "Unknown")
Commit: $(git -C "$APP_DIR" rev-parse HEAD 2>/dev/null || echo "Unknown")
EOF
    
    log "Manifest created: manifest_$DATE.txt"
}

# Verify backups
verify_backups() {
    log "Verifying backups..."
    
    # Check database backup
    if [[ -f "$BACKUP_DIR/database_$DATE.sql.gz" ]]; then
        if gzip -t "$BACKUP_DIR/database_$DATE.sql.gz"; then
            log "Database backup verification: OK"
        else
            error "Database backup is corrupted"
        fi
    fi
    
    # Check application backup
    if [[ -f "$BACKUP_DIR/application_$DATE.tar.gz" ]]; then
        if tar -tzf "$BACKUP_DIR/application_$DATE.tar.gz" >/dev/null; then
            log "Application backup verification: OK"
        else
            error "Application backup is corrupted"
        fi
    fi
    
    log "Backup verification completed"
}

# Send notification (optional)
send_notification() {
    if [[ -n "$NOTIFICATION_EMAIL" ]]; then
        local subject="Workly Backup Completed - $(hostname)"
        local message="Backup completed successfully at $(date)\nBackup files: $BACKUP_DIR/*_$DATE.*"
        
        echo -e "$message" | mail -s "$subject" "$NOTIFICATION_EMAIL" 2>/dev/null || \
            warn "Failed to send notification email"
    fi
}

# Main backup function
main() {
    case "${1:-full}" in
        "database"|"db")
            backup_database
            ;;
        "application"|"app")
            backup_application
            ;;
        "config")
            backup_config
            ;;
        "full")
            backup_database
            backup_application
            backup_config
            create_manifest
            verify_backups
            cleanup_old_backups
            send_notification
            ;;
        *)
            echo "Usage: $0 {full|database|application|config}"
            echo "  full        - Complete backup (default)"
            echo "  database    - Database only"
            echo "  application - Application files only"
            echo "  config      - Configuration files only"
            exit 1
            ;;
    esac
    
    log "Backup process completed successfully"
}

# Run main function
main "$@"