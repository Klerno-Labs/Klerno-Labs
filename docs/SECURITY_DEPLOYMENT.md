# 🔐 Security & Deployment Guide

## 🚨 Critical Security Notice

Before deploying to production, ensure the following security measures are implemented:

### 1. Environment Variables Configuration

Create a `.env` file with these required variables:

```bash
# Required: Change these for production!
ADMIN_EMAIL=your-admin@company.com
ADMIN_PASSWORD=your-secure-password-here

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/klerno_db

# Security Keys
SECRET_KEY=your-secret-key-here
JWT_SECRET=your-jwt-secret-here

# OAuth Configuration (if using)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# XRPL Configuration
XRPL_SECRET=your-xrpl-secret-here

# Environment
APP_ENV=production
DEBUG=false
```

### 2. Security Checklist

#### ✅ Authentication & Authorization
- [x] Password hashing with bcrypt
- [x] Session management with secure cookies
- [x] OAuth integration (Google, GitHub)
- [x] Role-based access control (admin, premium, viewer)
- [x] CSRF protection
- [x] Admin password warning system

#### ✅ Data Protection
- [x] SQL injection prevention (parameterized queries)
- [x] XSS protection (template escaping)
- [x] Input validation and sanitization
- [x] Password hash storage (never plain text)
- [x] Sensitive data exclusion from API responses

#### ✅ Network Security
- [x] HTTPS enforcement (in production)
- [x] CORS configuration
- [x] Rate limiting (implicit via FastAPI)
- [x] Secure headers configuration

#### ⚠️ To Configure for Production
- [ ] Set environment variables (see above)
- [ ] Configure SSL/TLS certificates
- [ ] Set up firewall rules
- [ ] Configure reverse proxy (nginx/traefik)
- [ ] Enable logging and monitoring

### 3. Production Deployment Steps

#### Step 1: Environment Setup
```bash
# Clone repository
git clone https://github.com/your-username/klerno-labs.git
cd klerno-labs

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

#### Step 2: Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your production values
nano .env

# Generate secure secrets
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(32))"
```

#### Step 3: Database Setup
```bash
# Initialize database
python -c "from app import store; store.init_db(); print('Database initialized')"

# Create admin user (will use ADMIN_EMAIL and ADMIN_PASSWORD from .env)
python -c "from app.main import *; print('Admin user created')"
```

#### Step 4: Production Server
```bash
# Install production WSGI server
pip install gunicorn

# Run with Gunicorn (recommended for production)
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Or use uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4. Docker Deployment

#### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Docker Compose
```yaml
version: '3.8'

services:
  klerno-app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/klerno
      - ADMIN_EMAIL=admin@klerno.com
      - ADMIN_PASSWORD=secure-password
    depends_on:
      - db

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=klerno
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### 5. Monitoring & Logging

#### Application Monitoring
```bash
# Add to requirements.txt for production monitoring
prometheus-client
structlog
sentry-sdk
```

#### Log Configuration
```python
# Add to app/main.py for structured logging
import structlog
import logging

logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
```

### 6. Backup Strategy

#### Database Backups
```bash
# PostgreSQL backup
pg_dump -U postgres -h localhost klerno > backup_$(date +%Y%m%d_%H%M%S).sql

# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups/klerno"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
pg_dump -U postgres -h localhost klerno > $BACKUP_DIR/klerno_$DATE.sql
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete  # Keep 7 days
```

### 7. Performance Optimization

#### Database Optimization
```sql
-- Add indexes for frequently queried columns
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_transactions_timestamp ON txs(timestamp);
CREATE INDEX idx_transactions_risk_score ON txs(risk_score);
CREATE INDEX idx_transactions_chain ON txs(chain);
```

#### Caching Configuration
```python
# Redis for production caching (optional)
# Install: pip install redis
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(REDIS_URL)
```

### 8. Security Headers

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
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    add_header Content-Security-Policy "default-src 'self'";
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 9. Health Checks

The application includes built-in health check endpoints:

- `GET /api/health-check` - Basic health status
- `GET /healthcheck` - UI health check page

### 10. Troubleshooting

#### Common Issues

1. **Database Connection Failed**
   - Check DATABASE_URL format
   - Verify database is running
   - Check firewall settings

2. **Import Errors**
   - Verify all dependencies installed
   - Check Python version (3.11+ required)
   - Activate virtual environment

3. **Permission Denied**
   - Check file permissions
   - Verify user has database access
   - Check port availability

4. **OAuth Errors**
   - Verify client ID/secret configuration
   - Check redirect URLs
   - Ensure HTTPS in production

### 11. Support

For technical support:
- GitHub Issues: Create an issue in the repository
- Documentation: Check README.md and code comments
- Logs: Check application logs for error details

---

**⚠️ Important**: Always test thoroughly in a staging environment before deploying to production!