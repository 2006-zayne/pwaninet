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

FORCE_REBUILD=false
if [ "${1:-}" = "--force" ] || [ "${1:-}" = "-f" ]; then
    FORCE_REBUILD=true
fi

# 3. Build container images on code updates (Docker layer cache makes code-only builds take ~1-2s)
if [ "$OLD_HEAD" != "$NEW_HEAD" ] || [ "$FORCE_REBUILD" = true ]; then
    echo "[2/6] Code updates detected. Building fresh container images..."
    docker compose -f "$COMPOSE_FILE" build web celery_worker
else
    echo "[2/6] No code changes detected. Rebuild skipped (use --force to override)."
fi

# 4. Database Migrations
echo "[3/6] Applying database migrations..."
docker compose -f "$COMPOSE_FILE" exec -T web python manage.py migrate --noinput || \
docker compose -f "$COMPOSE_FILE" run --rm web python manage.py migrate --noinput

# 5. Collect Static Files
echo "[4/6] Collecting static assets..."
docker compose -f "$COMPOSE_FILE" exec -T web python manage.py collectstatic --noinput || \
docker compose -f "$COMPOSE_FILE" run --rm web python manage.py collectstatic --noinput

# 6. Recreate Services with Updated Image
echo "[5/6] Refreshing web and celery services..."
docker compose -f "$COMPOSE_FILE" up -d --force-recreate web celery_worker

# 7. System Health Status
echo "[6/6] Verifying service statuses..."
docker compose -f "$COMPOSE_FILE" ps

echo "=================================================="
echo " [✓] Deployment Complete. Systems Operational."
echo "=================================================="
