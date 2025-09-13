# Klerno Labs - Horizontal Scaling Deployment Guide

## 🚀 Overview

This guide covers the deployment and scaling infrastructure for Klerno Labs, designed to achieve **99.99% uptime** through horizontal scaling, auto-scaling, and disaster recovery.

## 📋 Architecture Components

### Core Infrastructure
- **Load Balancer**: AWS ALB with SSL termination and health checks
- **Application Layer**: ECS Fargate with auto-scaling (2-10 instances)
- **Database**: PostgreSQL RDS with read replicas and automated backups
- **Cache**: Redis ElastiCache cluster with high availability
- **CDN**: CloudFront for static asset delivery
- **Monitoring**: CloudWatch, Prometheus, and Grafana
- **Disaster Recovery**: Cross-region backup and failover

### Local Development
- **Docker Compose**: Multi-service stack for local development
- **Load Balancer**: Nginx reverse proxy
- **Multiple App Instances**: Horizontal scaling simulation

---

## 🏗️ Local Development Setup

### Prerequisites
- Docker and Docker Compose
- Git
- Make (optional)

### Quick Start
```bash
# Clone the repository
git clone https://github.com/Klerno-Labs/Klerno-Labs.git
cd Klerno-Labs

# Start the full stack
docker-compose up -d

# Start with monitoring
docker-compose --profile monitoring up -d

# Start with background workers
docker-compose --profile worker up -d

# Start with read replica
docker-compose --profile replica up -d
```

### Available Services
- **Application**: http://localhost (load balanced)
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Database**: localhost:5432
- **Redis**: localhost:6379

### Health Checks
```bash
# Check application health
curl http://localhost/healthz

# Check detailed health
curl -H "X-API-Key: dev-api-key" http://localhost/health

# Check metrics
curl -H "X-API-Key: dev-api-key" http://localhost/metrics-detailed
```

---

## ☁️ Cloud Deployment (AWS)

### Prerequisites
- AWS CLI configured
- Terraform >= 1.0
- kubectl (for Kubernetes deployment)
- Docker

### 1. Infrastructure Deployment with Terraform

```bash
# Navigate to terraform directory
cd infrastructure/terraform

# Initialize Terraform
terraform init

# Plan the deployment
terraform plan -var="environment=production" \
               -var="domain_name=klerno.com" \
               -var="region=us-west-2"

# Apply the infrastructure
terraform apply
```

### 2. Container Registry Setup

```bash
# Login to ECR
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-west-2.amazonaws.com

# Build and push container
docker build -t klerno-labs:latest .
docker tag klerno-labs:latest <account-id>.dkr.ecr.us-west-2.amazonaws.com/klerno-labs:latest
docker push <account-id>.dkr.ecr.us-west-2.amazonaws.com/klerno-labs:latest
```

### 3. ECS Service Deployment

The Terraform configuration automatically sets up:
- ECS Cluster with Fargate
- Application Load Balancer
- Auto Scaling policies
- Health checks
- Service discovery

### 4. Kubernetes Deployment (Alternative)

```bash
# Apply Kubernetes manifests
kubectl apply -f infrastructure/kubernetes/base.yaml
kubectl apply -f infrastructure/kubernetes/ingress.yaml

# Check deployment status
kubectl get pods -n klerno-labs
kubectl get services -n klerno-labs
kubectl get hpa -n klerno-labs
```

---

## 🔄 Auto-Scaling Configuration

### ECS Auto Scaling
- **CPU Utilization**: Scale out at 70%, scale in at 30%
- **Memory Utilization**: Scale out at 80%, scale in at 40%
- **Request Count**: Scale out at 1000 requests/target/minute
- **Min Instances**: 2
- **Max Instances**: 10

### Kubernetes Auto Scaling
- **Horizontal Pod Autoscaler (HPA)**: CPU and memory based
- **Vertical Pod Autoscaler (VPA)**: Right-sizing containers
- **Cluster Autoscaler**: Node scaling

### Configuration
```yaml
# Example HPA configuration
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: klerno-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: klerno-app
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

## 📊 Monitoring and Observability

### Health Check Endpoints
- `/healthz` - Simple health check (200 OK)
- `/health` - Comprehensive health check with dependencies
- `/readiness` - Kubernetes readiness probe
- `/liveness` - Kubernetes liveness probe
- `/startup` - Kubernetes startup probe
- `/metrics-detailed` - Detailed system and application metrics

### CloudWatch Dashboards
Automatically created dashboards monitor:
- Application performance metrics
- Infrastructure health
- Database performance
- Cache utilization
- Error rates and latencies

### Alerting
Critical alerts are configured for:
- High error rates (>5%)
- High response times (>2 seconds)
- Low healthy target count (<2)
- High resource utilization (>80%)
- Database connection issues
- Cache availability

---

## 🗄️ Database Scaling

### Read Replicas
- Automatic read replica creation
- Read traffic routing for analytics
- Cross-region replicas for disaster recovery

### Connection Pooling
```python
# Built into the application
DATABASE_URL=postgresql://user:pass@host:5432/db?max_connections=20&min_connections=5
```

### Performance Optimization
- Strategic indexing
- Query optimization
- Connection pooling
- Prepared statements

---

## 💾 Caching Strategy

### Redis Configuration
- **Primary Use Cases**:
  - API response caching
  - Session storage
  - Rate limiting counters
  - Real-time analytics

### Multi-Level Caching
1. **Application Level**: In-memory caching for frequent data
2. **Redis Level**: Distributed caching across instances
3. **CDN Level**: Static asset caching at edge locations

---

## 🌐 CDN and Asset Optimization

### CloudFront Configuration
- Global edge locations
- Automatic compression
- Cache optimization for static assets
- Origin failover support

### Static Asset Strategy
```
/static/* → S3 → CloudFront → Global Edge Locations
```

---

## 🚨 Disaster Recovery

### Backup Strategy
- **RDS**: Automated daily backups with 30-day retention
- **Cross-Region**: Automated backup replication
- **Point-in-Time Recovery**: 35-day recovery window
- **Manual Snapshots**: Before major deployments

### Failover Configuration
- **Primary Region**: us-west-2
- **Backup Region**: us-east-1
- **RTO (Recovery Time Objective)**: < 1 hour
- **RPO (Recovery Point Objective)**: < 15 minutes

### Automated Failover
```python
# Disaster recovery Lambda function
def handle_disaster_recovery(event, context):
    # Promote read replica
    # Update DNS records
    # Scale backup infrastructure
    # Send notifications
```

---

## 🔧 Environment Configuration

### Environment Variables
```bash
# Production Environment
APP_ENV=production
PORT=8000
WORKERS=2
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
SECRET_KEY=...
API_KEY=...

# Scaling Configuration
MIN_REPLICAS=2
MAX_REPLICAS=10
TARGET_CPU_UTILIZATION=70
TARGET_MEMORY_UTILIZATION=80

# Monitoring
PROMETHEUS_ENABLED=true
METRICS_PORT=9090
HEALTH_CHECK_INTERVAL=30s
```

### Secrets Management
All sensitive data stored in AWS Secrets Manager:
- Database credentials
- API keys
- JWT secrets
- Third-party service keys

---

## 🚀 Deployment Strategies

### Blue-Green Deployment
```bash
# ECS Blue-Green deployment
aws ecs update-service \
  --cluster klerno-cluster-production \
  --service klerno-app-service \
  --deployment-configuration maximumPercent=200,minimumHealthyPercent=50
```

### Rolling Updates
```yaml
# Kubernetes rolling update
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 1
    maxSurge: 1
```

### Canary Deployments
```yaml
# Istio canary deployment
spec:
  http:
  - match:
    - headers:
        canary:
          exact: "true"
    route:
    - destination:
        host: klerno-app
        subset: v2
  - route:
    - destination:
        host: klerno-app
        subset: v1
```

---

## 📈 Performance Targets

### SLA Commitments
- **Uptime**: 99.99% (4.32 minutes downtime/month)
- **Response Time**: < 200ms (95th percentile)
- **Error Rate**: < 0.1%
- **Throughput**: 1000+ requests/second

### Capacity Planning
- **Current**: 3 instances, 1.5GB RAM, 0.5 vCPU each
- **Peak**: 10 instances, auto-scaling based on demand
- **Growth**: Designed for 10x traffic increase

---

## 🔍 Troubleshooting

### Common Issues

1. **High Response Times**
   ```bash
   # Check application metrics
   kubectl top pods -n klerno-labs
   
   # Check database performance
   aws rds describe-db-instances --db-instance-identifier klerno-db-production
   ```

2. **Failed Health Checks**
   ```bash
   # Check application logs
   kubectl logs -f deployment/klerno-app -n klerno-labs
   
   # Check dependencies
   curl http://app-service:8000/health
   ```

3. **Auto-scaling Issues**
   ```bash
   # Check HPA status
   kubectl describe hpa klerno-app-hpa -n klerno-labs
   
   # Check metrics server
   kubectl top nodes
   ```

### Log Analysis
```bash
# CloudWatch Insights queries
aws logs start-query \
  --log-group-name /ecs/klerno-app-production \
  --start-time 1640995200 \
  --end-time 1640998800 \
  --query-string 'fields @timestamp, @message | filter @message like /ERROR/'
```

---

## 📚 Additional Resources

- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Prometheus Monitoring](https://prometheus.io/docs/)
- [Grafana Dashboards](https://grafana.com/docs/)

---

## 🆘 Support and Contact

For deployment issues or questions:
- **Engineering Team**: engineering@klerno.com
- **DevOps Team**: devops@klerno.com
- **Emergency Pager**: +1-XXX-XXX-XXXX

---

*This deployment guide is continuously updated as the infrastructure evolves. Always refer to the latest version in the repository.*