"""
Production Monitoring Integration Guide

This guide explains how to integrate the comprehensive monitoring system
into your Klerno Labs FastAPI application.

## Overview

The monitoring system provides:
- ✅ Structured JSON logging with rotation
- ✅ Comprehensive metrics collection
- ✅ Multi-level health monitoring
- ✅ Real-time alerting system
- ✅ Monitoring API endpoints
- ✅ Notification channels (Email, Slack, Discord)

## Files Created

### Core Monitoring Components
- `app/monitoring/logging.py` - Advanced structured logging
- `app/monitoring/metrics.py` - Metrics collection system
- `app/monitoring/health.py` - Health monitoring checks
- `app/monitoring/endpoints.py` - FastAPI monitoring endpoints
- `app/monitoring/alerting.py` - Alerting and notifications
- `app/monitoring/config.json` - Monitoring configuration

## Integration Steps

### 1. Install Dependencies

Add to requirements.txt:
```
psutil>=5.9.0
aiohttp>=3.8.0
prometheus-client>=0.17.0
```

Install:
```bash
pip install psutil aiohttp prometheus-client
```

### 2. Initialize Monitoring in main.py

Add to the top of `app/main.py`:

```python
from app.monitoring.logging import production_logger, get_logger
from app.monitoring.metrics import metrics, track_endpoint_metrics
from app.monitoring.endpoints import router as monitoring_router
import time

# Initialize logging
logger = get_logger("main")

# Add monitoring router
app.include_router(monitoring_router)
```

### 3. Add Request Monitoring Middleware

Add to `app/main.py`:

```python
@app.middleware("http")
async def monitoring_middleware(request: Request, call_next):
    start_time = time.time()

    # Get request info
    endpoint = request.url.path
    method = request.method

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration_ms = (time.time() - start_time) * 1000

    # Track metrics
    track_endpoint_metrics(
        endpoint=endpoint,
        method=method,
        status_code=response.status_code,
        duration_ms=duration_ms
    )

    # Log request
    logger.info(
        f"{method} {endpoint} - {response.status_code}",
        extra={
            "endpoint": endpoint,
            "method": method,
            "status_code": response.status_code,
            "duration": duration_ms,
            "ip_address": request.client.host
        }
    )

    return response
```

### 4. Configure Environment Variables

Create `.env` file or set environment variables:

```bash
# Email notifications
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_EMAILS=admin@company.com,ops@company.com

# Slack notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK

# Discord notifications
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR/DISCORD/WEBHOOK
```

### 5. Add Monitoring to Error Handlers

Update error handlers in `app/main.py`:

```python
@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    logger.error(
        f"Internal server error: {str(exc)}",
        extra={
            "endpoint": request.url.path,
            "method": request.method,
            "error": str(exc)
        }
    )

    # Track error metric
    metrics.increment("http_errors_total", tags={
        "status_code": "500",
        "endpoint": request.url.path
    })

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
```

## Monitoring Endpoints

### Health Checks
- `GET /monitoring/health` - Comprehensive health status
- `GET /monitoring/health/live` - Simple liveness probe
- `GET /monitoring/health/ready` - Readiness probe

### Metrics
- `GET /monitoring/metrics` - Current metrics snapshot
- `GET /monitoring/metrics/export` - Export metrics to file

## Usage Examples

### Custom Metrics

```python
from app.monitoring.metrics import metrics

# Track business metrics
metrics.increment("user_registrations")
metrics.gauge("active_users", 1250)

# Time operations
with metrics.timer("database_query"):
    result = await db.execute(query)
```

### Custom Logging

```python
from app.monitoring.logging import get_logger

logger = get_logger("auth")

logger.info(
    "User login successful",
    extra={
        "user_id": user.id,
        "ip_address": request.client.host,
        "endpoint": "/auth/login"
    }
)
```

### Custom Alerts

```python
from app.monitoring.alerting import alert_manager, Alert, AlertSeverity

# Send custom alert
alert = Alert(
    title="Critical Business Event",
    message="Payment processing failure rate exceeded threshold",
    severity=AlertSeverity.CRITICAL,
    timestamp=datetime.utcnow(),
    source="payment_processor"
)

await alert_manager._send_alert(alert)
```

## Production Deployment

### Docker Integration

Add to Dockerfile:
```dockerfile
# Create logs directory
RUN mkdir -p /app/logs

# Expose monitoring port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/monitoring/health/live || exit 1
```

### Kubernetes Deployment

Add to deployment.yaml:
```yaml
spec:
  containers:
  - name: klerno-app
    livenessProbe:
      httpGet:
        path: /monitoring/health/live
        port: 8000
      initialDelaySeconds: 30
      periodSeconds: 10

    readinessProbe:
      httpGet:
        path: /monitoring/health/ready
        port: 8000
      initialDelaySeconds: 5
      periodSeconds: 5
```

### Log Aggregation

Configure log shipping to centralized logging:
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Splunk
- DataDog
- CloudWatch Logs

### Metrics Dashboard

Create dashboards for:
- Application performance metrics
- Business metrics
- Infrastructure metrics
- Error rates and alerts

## Security Considerations

- Monitor authentication failures
- Track suspicious IP addresses
- Alert on unusual access patterns
- Log all security-related events

## Performance Impact

The monitoring system is designed for minimal performance impact:
- Asynchronous logging
- Efficient metrics collection
- Background health checks
- Configurable retention periods

## Troubleshooting

### Common Issues

1. **High memory usage**: Reduce metrics retention time
2. **Slow health checks**: Increase timeout values
3. **Missing alerts**: Check notification channel configuration
4. **Log file growth**: Verify log rotation settings

### Debug Mode

Enable debug logging:
```python
import logging
logging.getLogger('klerno').setLevel(logging.DEBUG)
```

## Next Steps

1. Set up external monitoring tools (Prometheus, Grafana)
2. Configure log aggregation and analysis
3. Create custom dashboards for business metrics
4. Set up automated incident response
5. Implement distributed tracing for microservices

## Support

For questions or issues with the monitoring system:
1. Check logs in `/logs/` directory
2. Verify configuration in `app/monitoring/config.json`
3. Test endpoints manually: `curl /monitoring/health`
4. Review alerting configuration and channels
