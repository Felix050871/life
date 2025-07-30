#!/bin/bash
# Workly - Deployment Script

set -e

# Configuration
DEPLOY_ENV="${DEPLOY_ENV:-production}"
APP_DIR="${APP_DIR:-/home/workly/app}"
BACKUP_BEFORE_DEPLOY="${BACKUP_BEFORE_DEPLOY:-true}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-true}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Check deployment environment
check_environment() {
    log "Checking deployment environment..."
    
    if [[ "$DEPLOY_ENV" != "production" && "$DEPLOY_ENV" != "staging" ]]; then
        error "Invalid deployment environment: $DEPLOY_ENV"
    fi
    
    if [[ ! -d "$APP_DIR" ]]; then
        error "Application directory not found: $APP_DIR"
    fi
    
    if [[ ! -f "$APP_DIR/.env" ]]; then
        error "Environment file not found: $APP_DIR/.env"
    fi
    
    log "Environment check passed"
}

# Pre-deployment backup
pre_deploy_backup() {
    if [[ "$BACKUP_BEFORE_DEPLOY" == "true" ]]; then
        log "Creating pre-deployment backup..."
        
        if [[ -f "$APP_DIR/scripts/backup.sh" ]]; then
            cd "$APP_DIR"
            ./scripts/backup.sh full
        else
            warn "Backup script not found, skipping backup"
        fi
    fi
}

# Stop services
stop_services() {
    log "Stopping services..."
    
    # Stop application
    if systemctl is-active --quiet workly; then
        sudo systemctl stop workly
        log "Workly service stopped"
    fi
    
    # Stop worker if exists
    if systemctl is-active --quiet workly-worker; then
        sudo systemctl stop workly-worker
        log "Workly worker stopped"
    fi
}

# Pull latest code
update_code() {
    log "Updating application code..."
    
    cd "$APP_DIR"
    
    # Stash any local changes
    if git status --porcelain | grep -q .; then
        warn "Local changes detected, stashing..."
        git stash
    fi
    
    # Pull latest changes
    git fetch origin
    
    if [[ -n "${GIT_TAG:-}" ]]; then
        log "Deploying tag: $GIT_TAG"
        git checkout "$GIT_TAG"
    elif [[ -n "${GIT_BRANCH:-}" ]]; then
        log "Deploying branch: $GIT_BRANCH"
        git checkout "$GIT_BRANCH"
        git pull origin "$GIT_BRANCH"
    else
        log "Deploying latest main branch"
        git checkout main
        git pull origin main
    fi
    
    log "Code updated to commit: $(git rev-parse HEAD)"
}

# Update dependencies
update_dependencies() {
    log "Updating Python dependencies..."
    
    cd "$APP_DIR"
    source venv/bin/activate
    
    pip install --upgrade pip
    pip install -r requirements.txt --upgrade
    
    log "Dependencies updated"
}

# Run database migrations
run_migrations() {
    if [[ "$RUN_MIGRATIONS" == "true" ]]; then
        log "Running database migrations..."
        
        cd "$APP_DIR"
        source venv/bin/activate
        
        # Check if Alembic is configured
        if [[ -f "alembic.ini" ]]; then
            alembic upgrade head
        else
            warn "Alembic not configured, skipping migrations"
        fi
    fi
}

# Update static files
update_static_files() {
    log "Updating static files..."
    
    cd "$APP_DIR"
    
    # Collect and compress static files if needed
    if [[ -d "static" ]]; then
        find static -name "*.css" -o -name "*.js" | while read file; do
            if command -v gzip &> /dev/null; then
                gzip -9 -c "$file" > "$file.gz"
            fi
        done
    fi
    
    # Set proper permissions
    chown -R workly:workly static/
    chmod -R 644 static/
    
    log "Static files updated"
}

# Update configuration
update_config() {
    log "Updating configuration..."
    
    cd "$APP_DIR"
    
    # Reload systemd if service file changed
    if [[ -f "/etc/systemd/system/workly.service" ]]; then
        sudo systemctl daemon-reload
    fi
    
    # Reload nginx if config changed
    if [[ -f "/etc/nginx/sites-available/workly" ]]; then
        sudo nginx -t && sudo systemctl reload nginx
    fi
    
    log "Configuration updated"
}

# Start services
start_services() {
    log "Starting services..."
    
    # Start application
    sudo systemctl start workly
    
    # Wait for service to be ready
    sleep 5
    
    if systemctl is-active --quiet workly; then
        log "Workly service started successfully"
    else
        error "Failed to start Workly service"
    fi
    
    # Start worker if exists
    if [[ -f "/etc/systemd/system/workly-worker.service" ]]; then
        sudo systemctl start workly-worker
        if systemctl is-active --quiet workly-worker; then
            log "Workly worker started successfully"
        else
            warn "Failed to start Workly worker"
        fi
    fi
}

# Health check
health_check() {
    log "Performing health check..."
    
    local max_attempts=10
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if curl -f -s http://localhost:5000/health >/dev/null; then
            log "Health check passed"
            return 0
        fi
        
        ((attempt++))
        warn "Health check failed, attempt $attempt/$max_attempts"
        sleep 10
    done
    
    error "Health check failed after $max_attempts attempts"
}

# Post-deployment tasks
post_deploy_tasks() {
    log "Running post-deployment tasks..."
    
    cd "$APP_DIR"
    source venv/bin/activate
    
    # Clear any caches
    if [[ -d "instance/cache" ]]; then
        rm -rf instance/cache/*
    fi
    
    # Update search indices if needed
    # python manage.py update_search_index
    
    # Send deployment notification
    if [[ -n "${SLACK_WEBHOOK:-}" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"Workly deployed successfully to $DEPLOY_ENV\"}" \
            "$SLACK_WEBHOOK" || warn "Failed to send Slack notification"
    fi
    
    log "Post-deployment tasks completed"
}

# Rollback function
rollback() {
    error_msg="$1"
    
    error "Deployment failed: $error_msg"
    
    log "Attempting rollback..."
    
    # Stop services
    sudo systemctl stop workly 2>/dev/null || true
    
    # Restore from backup if available
    if [[ -f "$APP_DIR/scripts/restore.sh" ]]; then
        "$APP_DIR/scripts/restore.sh" latest
    else
        warn "Restore script not found, manual rollback required"
    fi
    
    # Restart services
    sudo systemctl start workly
    
    error "Rollback completed, please investigate the issue"
}

# Deployment summary
deployment_summary() {
    log "Deployment Summary"
    log "=================="
    log "Environment: $DEPLOY_ENV"
    log "Deployed to: $APP_DIR"
    log "Commit: $(git -C "$APP_DIR" rev-parse HEAD)"
    log "Deploy time: $(date)"
    log "Status: Success"
    
    # Log file sizes
    if [[ -d "$APP_DIR/logs" ]]; then
        log "Log files:"
        ls -lah "$APP_DIR/logs/" | tail -5
    fi
}

# Main deployment function
main() {
    local start_time=$(date +%s)
    
    log "Starting deployment to $DEPLOY_ENV environment"
    
    # Set error trap for rollback
    trap 'rollback "Deployment script failed"' ERR
    
    check_environment
    pre_deploy_backup
    stop_services
    update_code
    update_dependencies
    run_migrations
    update_static_files
    update_config
    start_services
    health_check
    post_deploy_tasks
    
    # Remove error trap
    trap - ERR
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    deployment_summary
    log "Deployment completed successfully in ${duration}s"
}

# Script options
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "rollback")
        if [[ -f "$APP_DIR/scripts/restore.sh" ]]; then
            "$APP_DIR/scripts/restore.sh" "${2:-latest}"
        else
            error "Restore script not found"
        fi
        ;;
    "health")
        health_check
        ;;
    "status")
        systemctl status workly
        ;;
    *)
        echo "Usage: $0 {deploy|rollback|health|status}"
        echo "  deploy   - Deploy application (default)"
        echo "  rollback - Rollback to previous version"
        echo "  health   - Check application health"
        echo "  status   - Show service status"
        exit 1
        ;;
esac