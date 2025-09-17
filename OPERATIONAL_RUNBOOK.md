# Klerno Labs - Quick Reference & Operational Runbook
========================================================

## 🚀 Quick Start Commands

### Development
```bash
# Start development environment
python -m app.main

# Run tests
python run_tests.py --suite all

# Performance profiling
python performance_profiler.py

# Monitoring dashboard
python production_monitoring_dashboard.py
```

### Production
```bash
# Deploy with Docker
docker-compose -f docker-compose.production.yml up -d

# Check service health
curl http://localhost:8000/health
curl http://localhost:8080/api/status

# View logs
docker-compose logs -f klerno-app

# Scale services
docker-compose scale klerno-app=3
```

### Backup & Recovery
```bash
# Create backup
python backup_disaster_recovery.py
# Select option 1: Create Full Backup

# List backups
python backup_disaster_recovery.py
# Select option 4: List Backups

# Restore backup
python backup_disaster_recovery.py
# Select option 6: Restore Backup
```

---

## 🔧 Operational Runbook

### Daily Operations Checklist

#### Morning Health Check (10 minutes)
- [ ] Check service status: `curl http://localhost:8000/health`
- [ ] Review overnight alerts in monitoring dashboard
- [ ] Verify backup completion: Check backup logs
- [ ] Monitor resource usage: CPU < 70%, Memory < 80%
- [ ] Check error rates: Should be < 1%

#### Performance Monitoring (15 minutes)
- [ ] Review response time trends (target < 500ms 95th percentile)
- [ ] Check SLA compliance in Grafana dashboard
- [ ] Monitor database query performance
- [ ] Review security logs for anomalies
- [ ] Validate all scheduled tasks completed

#### Weekly Maintenance (30 minutes)
- [ ] Review and cleanup old backups
- [ ] Update security patches if available
- [ ] Performance optimization review
- [ ] Disaster recovery test (quarterly)
- [ ] Documentation updates if needed

### Incident Response Procedures

#### Severity Levels
```yaml
Critical (P1):
  - Complete service outage
  - Data corruption/loss
  - Security breach
  - Response time: 15 minutes
  - Escalation: Immediate

High (P2):
  - Partial service degradation
  - High error rates (>5%)
  - Performance issues
  - Response time: 1 hour
  - Escalation: 2 hours

Medium (P3):
  - Minor feature issues
  - Monitoring alerts
  - Non-critical errors
  - Response time: 4 hours
  - Escalation: Next business day

Low (P4):
  - Enhancement requests
  - Documentation updates
  - Cosmetic issues
  - Response time: Next business day
  - Escalation: N/A
```

#### Incident Response Workflow

##### Step 1: Detection & Assessment (5 minutes)
```bash
# Check service status
curl -f http://localhost:8000/health || echo "Service DOWN"

# Check monitoring dashboard
open http://localhost:8080/

# Review error logs
docker-compose logs --tail=100 klerno-app | grep ERROR

# Assess severity and impact
```

##### Step 2: Initial Response (10 minutes)
```bash
# Create incident ticket
# Notify stakeholders based on severity
# Begin troubleshooting

# Common quick fixes:
# Restart services
docker-compose restart klerno-app

# Clear cache
docker exec klerno-redis redis-cli FLUSHALL

# Check disk space
df -h
```

##### Step 3: Investigation & Resolution
```bash
# Detailed log analysis
docker-compose logs klerno-app > incident_logs.txt

# Performance analysis
python performance_profiler.py

# Database integrity check
sqlite3 data/klerno.db "PRAGMA integrity_check;"

# Resource monitoring
docker stats --no-stream
```

##### Step 4: Recovery & Validation
```bash
# Apply fix and restart services
docker-compose up -d

# Validate service health
curl http://localhost:8000/health
curl http://localhost:8080/api/status

# Monitor for 15 minutes
watch -n 30 'curl -s http://localhost:8000/health'

# Update incident ticket with resolution
```

##### Step 5: Post-Incident Review
- [ ] Document root cause
- [ ] Identify prevention measures
- [ ] Update monitoring/alerting if needed
- [ ] Conduct blameless postmortem
- [ ] Update documentation

### Common Troubleshooting Scenarios

#### Scenario 1: High Response Times
```bash
# 1. Check system resources
docker stats --no-stream
free -h
iostat 1 5

# 2. Analyze slow queries
python -c "
import sqlite3
conn = sqlite3.connect('data/klerno.db')
conn.execute('EXPLAIN QUERY PLAN SELECT * FROM transactions LIMIT 10')
"

# 3. Check cache hit rates
docker exec klerno-redis redis-cli INFO stats

# 4. Review application logs for bottlenecks
docker-compose logs klerno-app | grep -E "(slow|timeout|performance)"

# 5. Scale up if needed
docker-compose scale klerno-app=3
```

#### Scenario 2: Database Issues
```bash
# 1. Check database file
ls -la data/klerno.db
file data/klerno.db

# 2. Verify integrity
sqlite3 data/klerno.db "PRAGMA integrity_check;"

# 3. Check locks
sqlite3 data/klerno.db "PRAGMA busy_timeout=30000;"

# 4. If corrupted, restore from backup
python backup_disaster_recovery.py
# Option 6: Restore Backup

# 5. Restart application
docker-compose restart klerno-app
```

#### Scenario 3: Authentication Issues
```bash
# 1. Check JWT secret configuration
echo $JWT_SECRET | wc -c  # Should be > 32 characters

# 2. Verify token expiration settings
grep JWT_EXPIRATION app/settings.py

# 3. Check Redis session storage
docker exec klerno-redis redis-cli KEYS "*session*"

# 4. Test authentication endpoint
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# 5. Review authentication logs
docker-compose logs klerno-app | grep -i auth
```

#### Scenario 4: Memory Leaks
```bash
# 1. Monitor memory usage over time
while true; do
  docker stats --no-stream --format "{{.Name}}: {{.MemUsage}}"
  sleep 60
done

# 2. Analyze memory consumption
python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"

# 3. Check for memory profiling
python -m memory_profiler app/main.py

# 4. Restart service with memory limit
docker-compose stop klerno-app
docker run --memory=1g klerno-app

# 5. Review code for potential leaks
grep -r "global\|cache\|@lru_cache" app/
```

### Maintenance Procedures

#### Security Updates
```bash
# 1. Review security advisories
# Check GitHub security tab
# Review dependency vulnerabilities

# 2. Update dependencies
pip list --outdated
pip install --upgrade package_name

# 3. Rebuild container
docker-compose build klerno-app

# 4. Deploy to staging first
docker-compose -f docker-compose.staging.yml up -d

# 5. Test thoroughly
python run_tests.py --suite security

# 6. Deploy to production
docker-compose -f docker-compose.production.yml up -d
```

#### Database Maintenance
```bash
# 1. Analyze database size
sqlite3 data/klerno.db "
SELECT name, count(*) as rows
FROM sqlite_master
CROSS JOIN pragma_table_info(sqlite_master.name)
WHERE sqlite_master.type='table'
GROUP BY name;
"

# 2. Vacuum database (reclaim space)
sqlite3 data/klerno.db "VACUUM;"

# 3. Update statistics
sqlite3 data/klerno.db "ANALYZE;"

# 4. Check index usage
sqlite3 data/klerno.db "
.headers on
SELECT * FROM sqlite_stat1;
"

# 5. Backup before maintenance
python backup_disaster_recovery.py
# Option 1: Create Full Backup
```

#### Performance Optimization
```bash
# 1. Run performance profiler
python performance_profiler.py

# 2. Analyze query performance
sqlite3 data/klerno.db "
.timer on
.headers on
EXPLAIN QUERY PLAN SELECT * FROM transactions
WHERE created_at > date('now', '-30 days');
"

# 3. Optimize slow endpoints
python -c "
import time
import requests
endpoints = ['/health', '/users/me', '/transactions']
for endpoint in endpoints:
    start = time.time()
    response = requests.get(f'http://localhost:8000{endpoint}')
    print(f'{endpoint}: {time.time() - start:.3f}s')
"

# 4. Update cache configuration
# Check Redis cache hit rates
docker exec klerno-redis redis-cli INFO stats | grep keyspace

# 5. Scale resources if needed
docker-compose scale klerno-app=4
```

---

## 📊 Monitoring Thresholds

### Application Metrics
```yaml
Response Time:
  Warning: > 300ms (95th percentile)
  Critical: > 500ms (95th percentile)

Error Rate:
  Warning: > 1%
  Critical: > 5%

Uptime:
  Warning: < 99.9%
  Critical: < 99%

Request Rate:
  Normal: 10-100 req/s
  High: > 200 req/s
  Critical: > 500 req/s
```

### System Metrics
```yaml
CPU Usage:
  Warning: > 70%
  Critical: > 90%

Memory Usage:
  Warning: > 75%
  Critical: > 90%

Disk Usage:
  Warning: > 80%
  Critical: > 95%

Database Size:
  Warning: > 1GB
  Critical: > 5GB
```

### Security Metrics
```yaml
Failed Logins:
  Warning: > 10/hour
  Critical: > 50/hour

Blocked IPs:
  Warning: > 5/hour
  Critical: > 20/hour

Admin Actions:
  Monitor: All admin actions
  Alert: Bulk operations
```

---

## 🔍 Log Analysis

### Important Log Patterns
```bash
# Application errors
grep -E "(ERROR|CRITICAL)" logs/app.log

# Authentication issues
grep -i "auth" logs/app.log | grep -E "(fail|error|denied)"

# Performance issues
grep -E "(slow|timeout|performance)" logs/app.log

# Security events
grep -E "(injection|xss|csrf|attack)" logs/app.log

# Database issues
grep -E "(database|sqlite|connection)" logs/app.log | grep -i error
```

### Log Rotation
```bash
# Configure logrotate
sudo tee /etc/logrotate.d/klerno > /dev/null <<EOF
/app/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 klerno klerno
    postrotate
        docker-compose restart klerno-app
    endscript
}
EOF
```

---

## 📞 Emergency Contacts

### Internal Team
```yaml
Primary On-Call: ops-team@klerno.com
Secondary On-Call: dev-team@klerno.com
Management: management@klerno.com
Security Team: security@klerno.com
```

### External Services
```yaml
Cloud Provider: AWS Support (Enterprise)
CDN Provider: CloudFlare Support
Monitoring: DataDog Support
Backup Service: S3 Support
```

### Escalation Matrix
```yaml
P1 (Critical):
  0-15 min: Primary On-Call
  15-30 min: Secondary On-Call + Manager
  30-60 min: Management + Executive
  >60 min: All hands + External support

P2 (High):
  0-60 min: Primary On-Call
  1-4 hours: Secondary On-Call
  >4 hours: Manager notification

P3/P4 (Medium/Low):
  Business hours: Standard support
  After hours: Next business day
```

---

## 📋 Checklist Templates

### Deployment Checklist
- [ ] Code review completed
- [ ] Tests passing (unit, integration, security)
- [ ] Performance testing completed
- [ ] Staging deployment successful
- [ ] Database migration tested
- [ ] Backup created before deployment
- [ ] Monitoring alerts configured
- [ ] Rollback plan documented
- [ ] Stakeholders notified
- [ ] Production deployment executed
- [ ] Health checks verified
- [ ] Performance validated
- [ ] Documentation updated

### Security Incident Checklist
- [ ] Incident detected and categorized
- [ ] Security team notified
- [ ] Affected systems identified
- [ ] Immediate containment actions taken
- [ ] Evidence preserved
- [ ] Stakeholders informed
- [ ] Root cause identified
- [ ] Remediation implemented
- [ ] Systems validated
- [ ] Post-incident review scheduled
- [ ] Documentation updated
- [ ] Prevention measures implemented

---

*Last Updated: September 16, 2025*
*Version: 1.0.0*
*© 2025 Klerno Labs. All rights reserved.*