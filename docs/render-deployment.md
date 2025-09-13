# Klerno Labs - Render.com Deployment Guide

This guide walks you through deploying Klerno Labs on Render.com, a modern cloud platform that makes deploying applications simple.

## Prerequisites

- A [Render.com](https://render.com) account
- Your GitHub repository connected to Render
- Basic understanding of environment variables

## Quick Deployment

### Step 1: Connect Repository

1. Log into your Render Dashboard
2. Click "New +" and select "Web Service"
3. Connect your GitHub repository (`Klerno-Labs/Klerno-Labs`)
4. Render will automatically detect the `render.yaml` configuration

### Step 2: Environment Variables

**Required Variables (Add in Render Dashboard):**

```bash
# Database (Auto-generated when you create PostgreSQL service)
DATABASE_URL=postgresql://username:password@host:port/dbname

# Security (Auto-generated or set manually)
SECRET_KEY=your-secret-key-32-characters-long
JWT_SECRET=your-jwt-secret-key
X_API_KEY=your-api-key-for-external-access

# Admin Bootstrap
BOOTSTRAP_ADMIN_EMAIL=your-admin@email.com
BOOTSTRAP_ADMIN_PASSWORD=your-secure-password
```

**Optional Variables:**

```bash
# Email Notifications (Recommended)
SENDGRID_API_KEY=your-sendgrid-api-key
ALERT_EMAIL_FROM=alerts@yourdomain.com
ALERT_EMAIL_TO=admin@yourdomain.com

# AI Features (Optional)
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o-mini

# Payment Processing (Optional)
STRIPE_SECRET_KEY=your-stripe-secret-key
STRIPE_PRICE_ID=your-stripe-price-id
STRIPE_WEBHOOK_SECRET=your-stripe-webhook-secret
```

### Step 3: Database Setup

1. In Render Dashboard, create a new PostgreSQL database:
   - Name: `klerno-labs-postgres`
   - Plan: `starter` (upgrade for production)
2. Copy the generated `DATABASE_URL`
3. Add it to your web service environment variables

### Step 4: Deploy

1. Click "Deploy" in Render Dashboard
2. Render will build using the Dockerfile and deploy automatically
3. Monitor the deployment logs for any issues

## Production Configuration

### Scaling for Production

Update your `render.yaml` or dashboard settings:

```yaml
# Web Service
plan: standard  # or 'pro' for high traffic
numInstances: 2  # Multiple instances for redundancy

# Database
plan: standard  # Better performance and backups
```

### Custom Domain

1. In Render Dashboard, go to your web service
2. Click "Settings" → "Custom Domains"
3. Add your domain (SSL is automatic)

### Monitoring

- **Health Checks**: Automatic via `/healthz` endpoint
- **Logs**: Available in Render Dashboard
- **Metrics**: Application metrics at `/metrics` endpoint
- **Alerts**: Configure via Render Dashboard

## Common Issues & Solutions

### Build Failures

**Issue**: Docker build fails
**Solution**: Check the build logs in Render Dashboard. Common fixes:
- Ensure all dependencies in `requirements.txt` are valid
- Check Dockerfile syntax
- Verify build target is set correctly

**Issue**: Memory limit exceeded during build
**Solution**: Upgrade to a higher plan or optimize dependencies

### Runtime Issues

**Issue**: Application won't start
**Solution**: Check environment variables are set correctly:
```bash
# Essential variables that must be set
APP_ENV=production
PORT=8000
DATABASE_URL=postgresql://...
```

**Issue**: Database connection errors
**Solution**: 
- Verify `DATABASE_URL` is correct
- Ensure PostgreSQL service is running
- Check network connectivity between services

### Performance Issues

**Issue**: Slow response times
**Solution**:
- Upgrade to `standard` or `pro` plan
- Add more instances
- Enable Redis caching (add Redis service)
- Monitor `/metrics` endpoint

## Advanced Configuration

### Redis Cache (Optional)

Add Redis service for improved performance:

1. Create Redis service in Render
2. Add environment variable:
   ```bash
   REDIS_URL=redis://...
   ```

### Background Jobs

For background processing, add a worker service:

```yaml
- type: worker
  name: klerno-labs-worker
  runtime: docker
  dockerfilePath: ./Dockerfile
  dockerContext: .
  startCommand: python -m celery worker -A app.worker --loglevel=info
```

## Support

- **Documentation**: Check the main README.md
- **Issues**: Create GitHub issue for bugs
- **Render Support**: [Render Help Center](https://help.render.com)

## Security Notes

🔒 **Important Security Reminders:**

1. **Never commit secrets** to your repository
2. **Set strong passwords** for admin accounts
3. **Use HTTPS** in production (automatic with Render)
4. **Regular updates** - keep dependencies updated
5. **Monitor logs** for suspicious activity

---

*For more deployment options, see the main [deployment documentation](./deployment.md).*