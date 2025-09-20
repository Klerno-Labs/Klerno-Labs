#!/bin/bash
# Blue-Green deployment script for Klerno Labs
# Safely deploys new app version with zero downtime and rollback support

set -e

APP_SERVICE="klerno-app"
NGINX_SERVICE="nginx"
BLUE_SUFFIX="-blue"
GREEN_SUFFIX="-green"

# Determine current live color
LIVE_COLOR=$(docker ps --format '{{.Names}}' | grep "${APP_SERVICE}${BLUE_SUFFIX}" && echo blue || echo green)
if [ "$LIVE_COLOR" = "blue" ]; then
  NEW_COLOR="green"
else
  NEW_COLOR="blue"
fi

NEW_SERVICE="${APP_SERVICE}-${NEW_COLOR}"
OLD_SERVICE="${APP_SERVICE}-${LIVE_COLOR}"

# Deploy new version
echo "[INFO] Deploying $NEW_SERVICE..."
docker-compose -f docker-compose.prod.yml up -d --no-deps --build $NEW_SERVICE

# Health check new version
echo "[INFO] Running health check on $NEW_SERVICE..."
HEALTHY=$(docker inspect --format='{{.State.Health.Status}}' $NEW_SERVICE)
if [ "$HEALTHY" != "healthy" ]; then
  echo "[ERROR] $NEW_SERVICE failed health check. Rolling back."
  docker-compose -f docker-compose.prod.yml stop $NEW_SERVICE
  exit 1
fi

# Switch Nginx upstream to new version
# (Assumes Nginx config uses upstreams for blue/green)
echo "[INFO] Switching Nginx to $NEW_SERVICE..."
docker exec $NGINX_SERVICE nginx -s reload

# Stop old version after switch
echo "[INFO] Stopping old service $OLD_SERVICE..."
docker-compose -f docker-compose.prod.yml stop $OLD_SERVICE

echo "[SUCCESS] Blue-Green deployment complete. $NEW_SERVICE is now live."
