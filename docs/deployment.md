# Deployment Guide

This guide covers deploying Klerno Labs with all the new advanced features.

## Quick Start

The easiest way to get started is with our automated setup script:

### Windows
```powershell
.\start.ps1
```

### Linux/macOS
```bash
./start.sh
```

## Manual Deployment

### Prerequisites

- **Python 3.11+** (3.12 recommended)
- **PostgreSQL** (for production) or SQLite (for development)
- **Redis** (optional, for caching and async tasks)
- **Docker** (optional, for containerized deployment)

### Environment Setup

1. **Clone the repository:**
```bash
git clone https://github.com/Klerno-Labs/Klerno-Labs.git
cd Klerno-Labs
```

2. **Create virtual environment:**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
```

3. **Install dependencies:**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. **Set up environment variables:**
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```env
# Application Settings
APP_ENV=production
DEMO_MODE=false
SECRET_KEY=your-32-char-secret-key

# Database
DATABASE_URL=postgresql://user:password@host:port/dbname

# XRPL Integration
XRPL_RPC_URL=wss://xrplcluster.com/

# OpenAI (for AI features)
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4o-mini

# Email Notifications
SENDGRID_API_KEY=your-sendgrid-key
ALERT_EMAIL_FROM=alerts@yourdomain.com

# Security
CSRF_PROTECTION=true
RATE_LIMITING=true
```

### Database Setup

#### PostgreSQL (Recommended for production)
```bash
# Create database
createdb klerno_labs

# Set DATABASE_URL in .env
DATABASE_URL=postgresql://username:password@localhost:5432/klerno_labs
```

#### SQLite (Development only)
```bash
# SQLite will be created automatically
DATABASE_URL=sqlite:///./klerno_labs.db
```

### Running the Application

#### Development
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Production
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker Deployment

#### Build and run with Docker Compose
```bash
docker-compose up -d
```

#### Or build manually
```bash
# Build image
docker build -t klerno-labs .

# Run container
docker run -d \
  --name klerno-labs \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e OPENAI_API_KEY=your-key \
  klerno-labs
```

## Production Configuration

### Reverse Proxy Setup

#### Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Systemd Service

Create `/etc/systemd/system/klerno-labs.service`:
```ini
[Unit]
Description=Klerno Labs AML Platform
After=network.target

[Service]
Type=exec
User=klerno
Group=klerno
WorkingDirectory=/opt/klerno-labs
Environment=PATH=/opt/klerno-labs/.venv/bin
ExecStart=/opt/klerno-labs/.venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable klerno-labs
sudo systemctl start klerno-labs
sudo systemctl status klerno-labs
```

## Cloud Deployment

### Railway
1. Connect your GitHub repository to Railway
2. Set environment variables in Railway dashboard
3. Deploy automatically on git push

### Render
1. Create a new Web Service on Render
2. Connect your repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`

### AWS/Azure/GCP
Use the provided Dockerfile with your cloud container service:
- AWS ECS/Fargate
- Azure Container Instances
- Google Cloud Run

## Database Migrations

For production deployments with schema changes:

```bash
# Generate migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Downgrade if needed
alembic downgrade -1
```

## Monitoring and Logging

### Health Checks
- `/health` - API health check (requires API key)
- `/healthz` - Simple health check (no auth)

### Metrics Endpoint
- `/metrics` - Prometheus-compatible metrics

### Log Configuration
```python
# In production, configure structured logging
import structlog

logger = structlog.get_logger()
```

## Security Checklist

### Pre-deployment Security
- [ ] Strong SECRET_KEY (32+ characters)
- [ ] HTTPS enabled with valid certificate
- [ ] CSRF protection enabled
- [ ] Rate limiting configured
- [ ] API keys rotated regularly
- [ ] Database credentials secured
- [ ] File permissions restricted (600 for sensitive files)

### Network Security
- [ ] Firewall configured (only necessary ports open)
- [ ] Database not exposed to internet
- [ ] Redis secured (if used)
- [ ] CORS configured properly

### Application Security
- [ ] Input validation enabled
- [ ] SQL injection protection
- [ ] XSS protection headers
- [ ] Content Security Policy
- [ ] Secure cookie settings

## Performance Optimization

### Application Level
```python
# Async/await usage
# Connection pooling
# Caching strategies
# Database indexing
```

### Infrastructure Level
- Load balancing with multiple app instances
- Database read replicas
- CDN for static assets
- Redis for caching and sessions

## Backup and Recovery

### Database Backups
```bash
# PostgreSQL backup
pg_dump klerno_labs > backup_$(date +%Y%m%d).sql

# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump klerno_labs | gzip > "$BACKUP_DIR/klerno_backup_$DATE.sql.gz"

# Keep only last 30 days
find $BACKUP_DIR -name "klerno_backup_*.sql.gz" -mtime +30 -delete
```

### Application Data Backup
```bash
# Backup uploaded files, logs, etc.
tar -czf app_data_$(date +%Y%m%d).tar.gz /opt/klerno-labs/data
```

## Troubleshooting

### Common Issues

#### Bootstrap/CSS Not Loading
```bash
# Check if static files are served correctly
curl -I http://localhost:8000/static/css/app.css

# Verify static file configuration in main.py
```

#### Database Connection Issues
```bash
# Test database connection
python -c "from app import store; store.init_db(); print('Database connected successfully')"
```

#### Plugin Loading Issues
```bash
# Check plugin directory permissions
ls -la app/plugins/

# Verify plugin syntax
python -m py_compile app/plugins/your_plugin.py
```

#### WebSocket Connection Issues
```bash
# Test WebSocket endpoint
wscat -c ws://localhost:8000/ws/alerts

# Check nginx configuration for WebSocket proxying
```

### Performance Issues

#### High Memory Usage
- Reduce batch sizes in analytics
- Implement pagination for large datasets
- Add database connection pooling

#### Slow Response Times
- Enable query logging
- Add database indexes
- Implement caching
- Profile with tools like `py-spy`

#### High CPU Usage
- Check for infinite loops in plugins
- Optimize analytics calculations
- Use async/await properly

### Debugging

#### Enable Debug Mode
```bash
# Add to .env
APP_ENV=development
DEBUG=true
```

#### View Logs
```bash
# Systemd logs
journalctl -u klerno-labs -f

# Application logs
tail -f /var/log/klerno-labs/app.log
```

#### Database Query Debugging
```python
# Add to settings for development
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

## Scaling

### Horizontal Scaling
- Multiple app instances behind load balancer
- Separate database server
- Redis cluster for caching
- Message queue for background tasks

### Vertical Scaling
- Increase CPU/memory
- Optimize database queries
- Implement connection pooling
- Use SSD storage

### Auto-scaling Configuration
```yaml
# Kubernetes example
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: klerno-labs-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: klerno-labs
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## Maintenance

### Regular Tasks
- [ ] Database vacuum/analyze (PostgreSQL)
- [ ] Log rotation
- [ ] Certificate renewal
- [ ] Dependency updates
- [ ] Security patches
- [ ] Backup verification

### Update Procedure
1. Backup database and application data
2. Test updates in staging environment
3. Schedule maintenance window
4. Apply updates with rolling deployment
5. Verify functionality
6. Monitor for issues

### Monitoring Alerts
Set up alerts for:
- High error rates
- Slow response times
- Database connection issues
- Disk space usage
- Memory usage
- Failed authentication attempts

## Support

### Log Analysis
```bash
# Error analysis
grep -E "(ERROR|CRITICAL)" /var/log/klerno-labs/app.log | tail -100

# Performance analysis
grep "slow query" /var/log/klerno-labs/app.log

# Security analysis
grep "authentication failed" /var/log/klerno-labs/app.log
```

### Performance Profiling
```python
# Add profiling middleware for development
from fastapi import Request
import time

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

### Contact Support
- **Documentation**: [docs.klerno.com](https://docs.klerno.com)
- **GitHub Issues**: [github.com/Klerno-Labs/Klerno-Labs/issues](https://github.com/Klerno-Labs/Klerno-Labs/issues)
- **Email**: support@klerno.com

---

For additional deployment assistance, please refer to our documentation or contact support.