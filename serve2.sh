#!/bin/bash

# Start Redis server
cd projects 
source venv/bin/activate
cd pwaninet
redis-server --daemonize yes

# Wait for Redis to be ready
sleep 2

# Check if Redis is running
if redis-cli ping > /dev/null 2>&1; then
    echo "Redis is running"
else
    echo "Failed to start Redis"
    exit 1
fi

# Set Celery environment variables
export CELERY_BROKER_URL=redis://127.0.0.1:6379/0
export CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0

# Start Celery worker
/home/zayne/projects/venv/bin/python -m celery -A pwaninet worker -l info
