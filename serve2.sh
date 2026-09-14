#!/bin/bash
# Terminal 2: Production Celery Worker & Redis Uplink

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load virtual environment if present
if [ -f ../venv/bin/activate ]; then
  source ../venv/bin/activate
elif [ -f venv/bin/activate ]; then
  source venv/bin/activate
fi

# Load environment variables if .env exists
if [ -f .env ]; then
  set -a
  source .env
  set +a
elif [ -f ../.env ]; then
  set -a
  source ../.env
  set +a
fi

# Explicit production environment configuration
export DJANGO_ENV=production
export DJANGO_SETTINGS_MODULE=pwaninet.settings.production

# Ensure Redis is running (either via local daemon or Docker container)
if ! redis-cli ping > /dev/null 2>&1; then
    redis-server --daemonize yes 2>/dev/null || true
    sleep 1
fi

if redis-cli ping > /dev/null 2>&1; then
    echo "[INFO] Redis is responsive."
else
    echo "[WARN] Direct redis-cli ping failed; relying on container/configured broker."
fi

# Set Celery environment variables
export CELERY_BROKER_URL=${CELERY_BROKER_URL:-redis://127.0.0.1:6379/0}
export CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND:-redis://127.0.0.1:6379/0}

# Start Celery worker consuming all production queues
exec /home/zayne/projects/venv/bin/python -m celery -A pwaninet worker -l info -Q default,media_queue,docs_queue,search_queue
