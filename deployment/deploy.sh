#!/bin/bash
# Klerno Labs Production Deployment Script
# Automated deployment with health checks and rollback capabilities

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DOCKER_COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.prod"
BACKUP_DIR="./backups"
DEPLOY_LOG="./logs/deploy.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$DEPLOY_LOG"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$DEPLOY_LOG"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$DEPLOY_LOG"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$DEPLOY_LOG"
}

# Pre-deployment checks
pre_deployment_checks() {
    log "🔍 Running pre-deployment checks..."
    
    # Check if required files exist
    if [[ ! -f "$PROJECT_DIR/$ENV_FILE" ]]; then
        error "Environment file $ENV_FILE not found!"
        error "Copy .env.prod.example to $ENV_FILE and configure it"
        exit 1
    fi
    
    if [[ ! -f "$PROJECT_DIR/$DOCKER_COMPOSE_FILE" ]]; then
        error "Docker Compose file $DOCKER_COMPOSE_FILE not found!"
        exit 1
    fi
    
    # Check Docker and Docker Compose
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    # Check disk space (minimum 2GB free)
    AVAILABLE_SPACE=$(df "$PROJECT_DIR" | awk 'NR==2 {print $4}')
    if [[ $AVAILABLE_SPACE -lt 2097152 ]]; then  # 2GB in KB
        error "Insufficient disk space. At least 2GB required for deployment"
        exit 1
    fi
    
    success "Pre-deployment checks passed"
}

# Create backup of current deployment
create_backup() {
    log "📦 Creating backup of current deployment..."
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    
    # Backup timestamp
    BACKUP_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_NAME="klerno_backup_$BACKUP_TIMESTAMP"
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR/$BACKUP_NAME"
    
    # Backup database if running
    if docker-compose -f "$DOCKER_COMPOSE_FILE" ps postgres | grep -q "Up"; then
        log "Backing up PostgreSQL database..."
        docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T postgres pg_dump -U klerno klerno_labs > "$BACKUP_DIR/$BACKUP_NAME/database.sql"
    fi
    
    # Backup application data
    if [[ -d "$PROJECT_DIR/data" ]]; then
        log "Backing up application data..."
        cp -r "$PROJECT_DIR/data" "$BACKUP_DIR/$BACKUP_NAME/"
    fi
    
    # Backup logs
    if [[ -d "$PROJECT_DIR/logs" ]]; then
        log "Backing up logs..."
        cp -r "$PROJECT_DIR/logs" "$BACKUP_DIR/$BACKUP_NAME/"
    fi
    
    # Compress backup
    tar -czf "$BACKUP_DIR/$BACKUP_NAME.tar.gz" -C "$BACKUP_DIR" "$BACKUP_NAME"
    rm -rf "$BACKUP_DIR/$BACKUP_NAME"
    
    success "Backup created: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
    echo "$BACKUP_NAME" > "$BACKUP_DIR/latest_backup.txt"
}

# Build and deploy
deploy() {
    log "🚀 Starting deployment..."
    
    cd "$PROJECT_DIR"
    
    # Set build variables
    export BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    export VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    
    # Build images
    log "Building Docker images..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" build --no-cache
    
    # Stop current services gracefully
    log "Stopping current services..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" down --remove-orphans
    
    # Start new deployment
    log "Starting new deployment..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    
    success "Deployment started"
}

# Health checks
health_checks() {
    log "🏥 Running health checks..."
    
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        log "Health check attempt $attempt/$max_attempts"
        
        # Check if all services are running
        if docker-compose -f "$DOCKER_COMPOSE_FILE" ps | grep -q "Exit"; then
            error "Some services failed to start"
            docker-compose -f "$DOCKER_COMPOSE_FILE" logs --tail=50
            return 1
        fi
        
        # Check application health endpoint
        if curl -f -s http://localhost:8000/healthz > /dev/null 2>&1; then
            success "Application health check passed"
            
            # Check database connection
            if docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T klerno-app python -c "
import sys
sys.path.append('/app')
from app.core.database import engine
try:
    with engine.connect() as conn:
        result = conn.execute('SELECT 1')
        print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
    sys.exit(1)
            "; then
                success "Database health check passed"
                return 0
            else
                warning "Database health check failed"
            fi
        else
            warning "Application health check failed"
        fi
        
        sleep 10
        ((attempt++))
    done
    
    error "Health checks failed after $max_attempts attempts"
    return 1
}

# Rollback function
rollback() {
    log "🔄 Starting rollback..."
    
    if [[ ! -f "$BACKUP_DIR/latest_backup.txt" ]]; then
        error "No backup found for rollback"
        exit 1
    fi
    
    BACKUP_NAME=$(cat "$BACKUP_DIR/latest_backup.txt")
    BACKUP_FILE="$BACKUP_DIR/$BACKUP_NAME.tar.gz"
    
    if [[ ! -f "$BACKUP_FILE" ]]; then
        error "Backup file not found: $BACKUP_FILE"
        exit 1
    fi
    
    log "Rolling back to backup: $BACKUP_NAME"
    
    # Stop current services
    docker-compose -f "$DOCKER_COMPOSE_FILE" down
    
    # Extract backup
    tar -xzf "$BACKUP_FILE" -C "$BACKUP_DIR"
    
    # Restore data
    if [[ -d "$BACKUP_DIR/$BACKUP_NAME/data" ]]; then
        rm -rf "$PROJECT_DIR/data"
        cp -r "$BACKUP_DIR/$BACKUP_NAME/data" "$PROJECT_DIR/"
    fi
    
    # Restore database
    if [[ -f "$BACKUP_DIR/$BACKUP_NAME/database.sql" ]]; then
        log "Restoring database..."
        docker-compose -f "$DOCKER_COMPOSE_FILE" up -d postgres
        sleep 10
        docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T postgres psql -U klerno -d klerno_labs < "$BACKUP_DIR/$BACKUP_NAME/database.sql"
    fi
    
    # Start services
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    
    # Clean up extracted backup
    rm -rf "$BACKUP_DIR/$BACKUP_NAME"
    
    success "Rollback completed"
}

# Main deployment function
main() {
    log "🎯 Klerno Labs Production Deployment Started"
    log "Timestamp: $(date)"
    log "Git Commit: $(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
    
    # Create logs directory
    mkdir -p "$(dirname "$DEPLOY_LOG")"
    
    case "${1:-deploy}" in
        "deploy")
            pre_deployment_checks
            create_backup
            deploy
            if health_checks; then
                success "🎉 Deployment completed successfully!"
                log "Application is available at: http://localhost:8000"
                log "Monitoring dashboard: http://localhost:3000"
                log "Metrics: http://localhost:9090"
            else
                error "❌ Deployment failed health checks"
                log "Starting rollback..."
                rollback
                exit 1
            fi
            ;;
        "rollback")
            rollback
            if health_checks; then
                success "Rollback completed successfully"
            else
                error "Rollback failed health checks"
                exit 1
            fi
            ;;
        "health")
            health_checks
            ;;
        "backup")
            create_backup
            ;;
        "logs")
            docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f
            ;;
        "status")
            docker-compose -f "$DOCKER_COMPOSE_FILE" ps
            ;;
        *)
            echo "Usage: $0 {deploy|rollback|health|backup|logs|status}"
            echo "  deploy   - Full deployment with backup and health checks"
            echo "  rollback - Rollback to previous deployment"
            echo "  health   - Run health checks only"
            echo "  backup   - Create backup only"
            echo "  logs     - Show application logs"
            echo "  status   - Show service status"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"