# Klerno Labs Deployment Guide

## Quick Start

### Development (Windows)
```cmd
docker-compose up -d
```

### Production
```cmd
scripts\deploy.bat production
```

## Architecture

- Application: FastAPI with async processing
- Database: SQLite/PostgreSQL with automated backups
- Cache: Redis for performance optimization
- Container: Docker with multi-stage builds
- CI/CD: GitHub Actions with security scanning
- Monitoring: Health checks and metrics collection

## Environment Variables

Required for production:
- DATABASE_URL: Database connection string
- REDIS_URL: Redis connection string (optional)
- ENVIRONMENT: production/staging/development
- LOG_LEVEL: INFO/DEBUG/WARNING

## Files Created

1. .github/workflows/ci-cd.yml - Automated testing and building
2. Dockerfile - Container configuration
3. docker-compose.yml - Development environment
4. scripts/deploy.bat - Deployment automation
5. monitoring/config.yml - Monitoring setup
6. nginx.conf - Reverse proxy configuration

## Next Steps

1. Copy .env.template to .env and configure
2. Run: docker-compose up -d
3. Check health: http://localhost:8000/health
4. View application: http://localhost:8000

## Support

For deployment issues:
1. Check application logs: docker logs klerno-labs_app_1
2. Check health endpoint: curl http://localhost:8000/health
3. Review environment variables in .env file
