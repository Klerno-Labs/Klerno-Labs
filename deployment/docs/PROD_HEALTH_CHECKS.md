# Klerno Labs Production Health Checks

## Overview

This document describes the health check endpoints and monitoring strategy for Klerno Labs production deployments.

## Health Endpoints

- `/healthz` — Main application health (returns 200 OK if healthy)
- `/metrics` — Prometheus metrics endpoint
- `/analytics/api/metrics` — Real-time analytics and system health

## Docker Compose Health Checks

- All services in `docker-compose.prod.yml` have health checks defined
- Nginx, PostgreSQL, Redis, and app containers are monitored

## Monitoring Stack

- Prometheus scrapes `/metrics` for system and app metrics
- Grafana dashboards visualize health, performance, and alerts
- Loki/Promtail aggregate logs for troubleshooting

## Best Practices

- Never deploy if health checks fail
- Use blue-green/canary scripts to automate health validation
- Alert on high error rates, latency, or resource usage
- Regularly review health dashboards and logs

---
For questions, contact the DevOps team.
