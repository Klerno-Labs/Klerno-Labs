# Klerno Labs Canary Release Strategy

## Overview

This document describes the canary release process for Klerno Labs, enabling safe, incremental rollouts of new versions to a subset of users before full deployment.

## How It Works

- Deploy new app version as a separate canary service (e.g., `klerno-app-canary`)
- Nginx routes a small percentage of traffic to the canary
- Monitor health, errors, and performance
- Gradually increase canary traffic if stable
- Promote canary to production or rollback if issues detected

## Usage


1. Deploy the canary service:

```sh
docker-compose -f docker-compose.prod.yml up -d --no-deps --build klerno-app-canary
```


1. Update Nginx config to split traffic (e.g., 90% to main, 10% to canary):

```nginx
upstream klerno_app {
    server klerno-app:8000 weight=9;
    server klerno-app-canary:8000 weight=1;
}
```

1. Monitor canary metrics in Grafana and logs in Loki.
1. If stable, promote canary to main by updating service and Nginx config.
1. If issues, stop canary and revert Nginx config.

## Best Practices

- Start with 5-10% traffic to canary
- Monitor error rates, latency, and user feedback
- Automate rollback on health check failures
- Document all changes and incidents

---
For questions, contact the DevOps team.
