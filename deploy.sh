#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/srv/prod-app/src"
COMPOSE_FILE="$APP_DIR/docker-compose.prod.yml"

cd "$APP_DIR"

echo "=================================================="
echo " [Pwaninet] Initiating Automated Production Deploy"
echo "=================================================="

# 1. Check for dirty local working directory
if ! git diff-index --quiet HEAD --; then
    echo "[!] ERROR: Local uncommitted changes detected in $APP_DIR. Aborting deploy."
    git status -s
    exit 1
fi

# 2. Record HEAD hash before pulling
OLD_HEAD=$(git rev-parse HEAD)

echo "[1/6] Pulling latest code from origin/main..."
git pull origin main

NEW_HEAD=$(git rev-parse HEAD)

if [ "$OLD_HEAD" = "$NEW_HEAD" ]; then
    echo "[i] Already up to date. Proceeding with service refresh check."
fi

# 3. Check if rebuild is necessary
REBUILD_NEEDED=false
if [ "$OLD_HEAD" != "$NEW_HEAD" ]; then
    CHANGED_FILES=$(git diff --name-only "$OLD_HEAD" "$NEW_HEAD")
    if echo "$CHANGED_FILES" | grep -Eq 'requirements\.txt|Dockerfile'; then
        REBUILD_NEEDED=true
    fi
fi

if [ "$REBUILD_NEEDED" = true ]; then
    echo "[2/6] Dependency or Dockerfile change detected. Rebuilding container images..."
    docker compose -f "$COMPOSE_FILE" build web celery_worker
else
    echo "[2/6] No dependency changes detected. Skipping container rebuild."
fi

# 4. Database Migrations
echo "[3/6] Applying database migrations..."
docker compose -f "$COMPOSE_FILE" exec -T web python manage.py migrate --noinput || \
docker compose -f "$COMPOSE_FILE" run --rm web python manage.py migrate --noinput

# 5. Collect Static Files
echo "[4/6] Collecting static assets..."
docker compose -f "$COMPOSE_FILE" exec -T web python manage.py collectstatic --noinput || \
docker compose -f "$COMPOSE_FILE" run --rm web python manage.py collectstatic --noinput

# 6. Recreate / Restart Services
echo "[5/6] Refreshing web and celery services..."
if [ "$REBUILD_NEEDED" = true ]; then
    docker compose -f "$COMPOSE_FILE" up -d --force-recreate web celery_worker
else
    docker compose -f "$COMPOSE_FILE" restart web celery_worker
fi

# 7. System Health Status
echo "[6/6] Verifying service statuses..."
docker compose -f "$COMPOSE_FILE" ps

echo "=================================================="
echo " [✓] Deployment Complete. Systems Operational."
echo "=================================================="
