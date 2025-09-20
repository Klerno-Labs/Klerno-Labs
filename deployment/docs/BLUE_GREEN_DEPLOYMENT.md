# Klerno Labs Blue-Green Deployment

## Overview

This document describes the blue-green deployment strategy for Klerno Labs, enabling zero-downtime deployments and safe rollbacks.

## How It Works

- Two app services: `klerno-app-blue` and `klerno-app-green`
- Only one is live at a time (Nginx routes traffic)
- Deploy new version to the idle color
- Health check new version
- Switch Nginx to new version
- Stop old version after switch

## Usage

1. Update your code and build the new image.
2. Run the deployment script:

```sh
bash deployment/blue_green_deploy.sh
````

1. The script will:
    - Deploy the new color (`blue` or `green`)
    - Health check the new service
    - Reload Nginx to switch traffic
    - Stop the old service


## Rollback

- If the new version fails health checks, the script aborts and keeps the old version running.
- To manually rollback, re-run the script or start the previous color service.


## Nginx Configuration

- Nginx must be configured with upstreams for both `klerno-app-blue` and `klerno-app-green`.
- Example upstream block:

```nginx
upstream klerno_app {
    server klerno-app-blue:8000 backup;
    server klerno-app-green:8000 backup;
}
```

## Best Practices

- Always test in staging before production
- Monitor health checks and logs after deployment
- Use canary releases for gradual rollout if needed

---
For questions, contact the DevOps team.
