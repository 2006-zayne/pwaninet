# Celery Setup Guide for Document Processing

This guide explains how to set up and use Celery for asynchronous document processing in the Pwaninet application.

## Overview

Celery is used to handle background tasks for document processing:
- Generating PDF thumbnails and previews
- Extracting metadata from uploaded files
- Computing file checksums
- Updating document processing status

## Prerequisites

### 1. Redis Server
Celery requires a message broker. Redis is configured as the default broker.

**Install Redis:**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# Start Redis
redis-server --daemonize yes
```

**Verify Redis is running:**
```bash
redis-cli ping
# Should return: PONG
```

### 2. Celery Installation
Celery is already included in `requirements.txt`:
```
celery==5.3.4
```

If not installed:
```bash
pip install celery==5.3.4
```

## Configuration

Celery is configured in `pwaninet/settings/base.py`:

```python
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
```

## Starting the Celery Worker

### Development

**Start Celery worker (using python module):**
```bash
cd /home/zayne/projects/pwaninet
python -m celery -A pwaninet worker -l info
```

**Start Celery worker with detailed logging:**
```bash
python -m celery -A pwaninet worker -l debug
```

**Start Celery worker with specific concurrency:**
```bash
python -m celery -A pwaninet worker -l info -c 4
```

**Start Celery worker in background:**
```bash
python -m celery -A pwaninet worker -l info --detach
```

### Production

**Start Celery worker as a daemon (systemd):**

Create `/etc/systemd/system/celery.service`:
```ini
[Unit]
Description=Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=your_user
Group=your_group
WorkingDirectory=/home/zayne/projects/pwaninet
Environment="PATH=/home/zayne/projects/venv/bin"
ExecStart=/home/zayne/projects/venv/bin/python -m celery -A pwaninet worker -l info --pidfile=/var/run/celery/%n.pid --logfile=/var/log/celery/%n.log
Restart=always

[Install]
WantedBy=multi-user.target
```

**Enable and start the service:**
```bash
sudo systemctl enable celery
sudo systemctl start celery
sudo systemctl status celery
```

**Start Celery worker with supervisor:**

Create `/etc/supervisor/conf.d/celery.conf`:
```ini
[program:celery]
command=/home/zayne/projects/venv/bin/python -m celery -A pwaninet worker -l info
directory=/home/zayne/projects/pwaninet
user=your_user
numprocs=1
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600
stdout_logfile=/var/log/celery/worker.log
stderr_logfile=/var/log/celery/worker_error.log
```

**Start supervisor:**
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start celery
```

## Flower (Web Monitoring)

### Install Flower

```bash
pip install flower
```

Or add to requirements.txt:
```
flower==2.0.1
```

### Start Flower

**Start Flower (basic):**
```bash
python -m flower -A pwaninet
```

**Start Flower with specific port:**
```bash
python -m flower -A pwaninet --port=5555
```

**Start Flower in background:**
```bash
python -m flower -A pwaninet --port=5555 --detach
```

### Access Flower UI

Open your browser to:
```
http://localhost:5555
```

Flower provides:
- Real-time task monitoring
- Worker status and statistics
- Task execution history
- Task success/failure rates
- Performance metrics

### Flower Authentication (Optional)

**Start with basic auth:**
```bash
python -m flower -A pwaninet --basic_auth=user:password
```

**Start with more secure options:**
```bash
python -m flower -A pwaninet --basic_auth=admin:securepassword --port=5555
```

## Celery Tasks

Document processing tasks are defined in `documents/tasks/processing.py`:

### `process_document`
Main task that coordinates the entire processing pipeline:
- Gets latest document version
- Processes each file in the version
- Indexes document for search
- Marks document as ready

**Usage:**
```python
from documents.tasks.processing import process_document

# Trigger task
result = process_document.delay(document_id)

# Check status
print(result.status)  # PENDING, STARTED, SUCCESS, FAILURE
print(result.result)  # Task result when complete
```

### `process_file`
Processes a single document file:
- Generates thumbnail
- Generates preview
- Extracts metadata
- Checks for duplicates

**Usage:**
```python
from documents.tasks.processing import process_file

# Trigger task
result = process_file.delay(file_id)
```

### Other Tasks
- `generate_thumbnail` - Creates thumbnail images
- `generate_preview` - Creates PDF previews
- `extract_metadata` - Extracts document metadata
- `check_duplicate` - Checks for duplicate files
- `update_search_index` - Updates search index
- `remove_from_search_index` - Removes from search index

## Monitoring Celery

### Command Line Monitoring

**Check active tasks:**
```bash
python -m celery -A pwaninet inspect active
```

**Check registered tasks:**
```bash
python -m celery -A pwaninet inspect registered
```

**Check worker statistics:**
```bash
python -m celery -A pwaninet inspect stats
```

**Check worker status:**
```bash
python -m celery -A pwaninet inspect ping
```

### Flower Web UI

Flower provides a comprehensive web interface for monitoring:
- Task queue status
- Worker health
- Task execution times
- Success/failure rates
- Real-time task tracking

## Troubleshooting

### Worker not starting

**Check Redis connection:**
```bash
redis-cli ping
```

**Start Redis if not running:**
```bash
redis-server --daemonize yes
```

**Check Celery configuration:**
```bash
python -m celery -A pwaninet inspect conf
```

**Check for port conflicts:**
```bash
lsof -i :6379
```

### Tasks not executing

**Check worker logs:**
```bash
# If running in foreground, check terminal output
# If running as daemon, check log files
tail -f /var/log/celery/worker.log
```

**Check task queue:**
```bash
python -m celery -A pwaninet inspect active
```

**Purge stuck tasks:**
```bash
python -m celery -A pwaninet purge
```

### Task failures

**Check task result:**
```python
from celery.result import AsyncResult
result = AsyncResult(task_id)
print(result.status)
print(result.result)
print(result.traceback)  # Error traceback
```

**Retry failed task:**
```python
from documents.tasks.processing import process_document
result = process_document.retry(args=[document_id], countdown=60)
```

### Redis connection issues

**Check if Redis is running:**
```bash
redis-cli ping
```

**Start Redis:**
```bash
redis-server --daemonize yes
```

**Check Redis logs:**
```bash
tail -f /var/log/redis/redis-server.log
```

## Development Workflow

### 1. Start Redis
```bash
redis-server --daemonize yes
```

### 2. Start Django Development Server
```bash
cd /home/zayne/projects/pwaninet
python manage.py runserver
```

### 3. Start Celery Worker (separate terminal)
```bash
cd /home/zayne/projects/pwaninet
python -m celery -A pwaninet worker -l info
```

### 4. (Optional) Start Flower for monitoring (another terminal)
```bash
cd /home/zayne/projects/pwaninet
python -m flower -A pwaninet --port=5555
```

### 5. Upload Documents
- Navigate to upload page
- Select files and metadata
- Submit upload
- Progress bar will show real task progress
- Documents will be processed in background

### 6. Monitor Processing
- Check Celery worker logs for processing status
- Use Flower UI at http://localhost:5555 for visual monitoring
- Documents will appear in search when status='ready'

## Environment Variables

Configure Celery via environment variables in `.env`:

```bash
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
```

## Production Considerations

1. **Use separate Redis instances** for broker and result backend
2. **Configure task timeouts** appropriately for your workload
3. **Monitor worker memory** and restart if needed
4. **Use multiple workers** for high-throughput scenarios
5. **Set up proper logging** and log rotation
6. **Use Flower with authentication** in production
7. **Configure worker autoscaling** based on load
8. **Set up monitoring alerts** for worker failures
9. **Use process pools** for CPU-intensive tasks
10. **Configure task queues** for different task priorities

## Quick Start Commands

```bash
# Start Redis
redis-server --daemonize yes

# Start Celery worker
python -m celery -A pwaninet worker -l info

# Start Flower (optional)
python -m flower -A pwaninet --port=5555

# Check worker status
python -m celery -A pwaninet inspect ping

# Check active tasks
python -m celery -A pwaninet inspect active

# Purge stuck tasks
python -m celery -A pwaninet purge
```

## Common Issues and Solutions

### Issue: "Command not found: celery"
**Solution:** Use `python -m celery` instead of `celery`

### Issue: "Error connecting to redis"
**Solution:** Start Redis with `redis-server --daemonize yes`

### Issue: Tasks stuck in PENDING
**Solution:** Check worker is running and can connect to Redis

### Issue: Worker consuming too much memory
**Solution:** Restart worker periodically or use `--max-tasks-per-child`

### Issue: Tasks failing with timeout
**Solution:** Increase `CELERY_TASK_TIME_LIMIT` in settings
