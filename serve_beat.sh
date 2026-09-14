#!/bin/bash
# Terminal 4: Production Celery Beat Scheduler Daemon

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

# Start Celery beat scheduler
exec /home/zayne/projects/venv/bin/python -m celery -A pwaninet beat -l info
