# Pwaninet Running Guide

## Project Overview

Pwaninet is a Django-based social networking platform with real-time WebSocket capabilities. The architecture uses:

- **Django API**: REST API backend (runs on host in development)
- **PostgreSQL**: Primary database (runs in Docker)
- **Redis**: Caching and channel layer for WebSockets (runs in Docker)
- **Celery**: Background task processing (optional, runs on host)
- **WebSockets**: Real-time features via uvicorn ASGI server (runs on host)

### What Runs Where

| Service | Development Mode | Production Mode |
|---------|------------------|-----------------|
| Django API | Host (python manage.py runserver) | Docker (gunicorn/daphne) |
| WebSockets | Host (uvicorn) | Docker (daphne) |
| PostgreSQL | Docker (db service) | Docker (db service) |
| Redis | Docker (redis service) | Docker (redis service) |
| Celery Worker | Host (optional) | Docker (celery service) |
| Celery Beat | Host (optional) | Docker (celery-beat service) |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Host Machine                          │
│                                                              │
│  ┌──────────────────┐    ┌──────────────────┐             │
│  │  Django API      │    │  WebSockets      │             │
│  │  (runserver)     │    │  (uvicorn)       │             │
│  │  Port: 8000      │    │  Port: 8000      │             │
│  └────────┬─────────┘    └────────┬─────────┘             │
│           │                       │                         │
│           └───────────┬───────────┘                         │
│                       │                                     │
│           ┌───────────▼───────────┐                         │
│           │   Celery (optional)    │                         │
│           │   Worker + Beat        │                         │
│           └───────────┬───────────┘                         │
└───────────────────────┼─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼────────┐ ┌────▼────────┐ ┌──▼──────────┐
│  Docker: db    │ │Docker: redis │ │  .env.local  │
│  PostgreSQL    │ │  Redis       │ │  (host env)  │
│  Port: 5432    │ │  Port: 6379  │ │              │
└────────────────┘ └─────────────┘ └─────────────┘
```

## Setup Instructions

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- PostgreSQL client (optional, for debugging)

### Step 1: Install Dependencies

```bash
# Navigate to project directory
cd /home/zayne/projects/pwaninet

# Create virtual environment (if not exists)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### Step 2: Start Docker Services

```bash
# Start PostgreSQL and Redis in Docker
docker compose up -d db redis

# Verify services are running
docker compose ps
```

Expected output:
```
NAME                STATUS
pwaninet-db-1       Up
pwaninet-redis-1    Up
```

### Step 3: Configure Environment

```bash
# For local development, ensure .env.local is active
# The project automatically loads .env.local via Django-environ

# Verify .env.local exists
cat .env.local
```

### Step 4: Apply Database Migrations

```bash
# Activate virtual environment
source venv/bin/activate

# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser
```

### Step 5: Run Backend (Normal API)

```bash
# For standard REST API endpoints
python manage.py runserver
```

The API will be available at: `http://localhost:8000`

### Step 6: Run WebSockets (for real-time features)

```bash
# Stop the runserver process if running (Ctrl+C)

# Run with uvicorn for WebSocket support
uvicorn pwaninet.asgi:application --reload --host 0.0.0.0 --port 8000
```

WebSocket endpoints:
- `ws://localhost:8000/ws/notifications/`
- `ws://localhost:8000/ws/feed/`
- `ws://localhost:8000/ws/online/`
- Messaging WebSocket endpoints (see routing.py)

### Step 7: Run Celery (Optional)

```bash
# In a separate terminal, activate virtual environment
source venv/bin/activate

# Run Celery worker
celery -A pwaninet worker -l info

# In another terminal, run Celery beat (for scheduled tasks)
celery -A pwaninet beat -l info
```

## Environment Rules

### Environment Files

The project uses **two** environment files:

1. **`.env.local`** - For local development (host-based)
   - DB_HOST=localhost
   - REDIS_HOST=127.0.0.1
   - Used when running Django on host machine

2. **`.env.docker`** - For Docker-based deployment
   - DB_HOST=db
   - REDIS_HOST=redis
   - Used when running Django inside Docker containers

### Critical Rules

- **NO mixing allowed**: Never use `.env.local` with Docker services or `.env.docker` with host-based Django
- **One key = One value**: No duplicate keys in any environment file
- **No fallback expressions**: Docker Compose uses `${VAR}` without defaults like `${VAR:-default}`
- **Only one active runtime config**: Choose either local OR Docker mode, never both simultaneously

### How to Switch Modes

**Local Development (Default)**:
```bash
# Ensure .env.local exists and is configured
# Run Django on host
docker compose up -d db redis
python manage.py runserver
```

**Docker Deployment**:
```bash
# Use .env.docker
# Run Django in Docker (not covered in this guide - for production)
docker compose up -d
```

## Debugging

### Check Database Connection

```bash
# Test PostgreSQL connection
docker exec -it pwaninet-db-1 psql -U postgres -d pwaninet_db

# Inside psql, run:
\dt  # List tables
\q   # Quit
```

### Verify Redis

```bash
# Test Redis connection
docker exec -it pwaninet-redis-1 redis-cli

# Inside redis-cli, run:
PING  # Should return PONG
DBSIZE  # Show number of keys
EXIT  # Quit
```

### Detect Ghost Servers

```bash
# Check what's running on port 8000 (Django)
lsof -i :8000

# Check PostgreSQL port
lsof -i :5432

# Check Redis port
lsof -i :6379
```

### Kill Stale Ports

```bash
# Kill process on port 8000
lsof -ti :8000 | xargs kill -9

# Kill process on port 5432 (PostgreSQL)
lsof -ti :5432 | xargs kill -9

# Kill process on port 6379 (Redis)
lsof -ti :6379 | xargs kill -9
```

### Check Docker Logs

```bash
# View logs for all services
docker compose logs

# View logs for specific service
docker compose logs db
docker compose logs redis

# Follow logs in real-time
docker compose logs -f
```

### Django Debugging

```bash
# Check Django settings
python manage.py check

# Show current database configuration
python manage.py shell -c "from django.conf import settings; print(settings.DATABASES)"

# Test database connection
python manage.py dbshell
```

### WebSocket Debugging

```bash
# Test WebSocket connection using wscat (install with: npm install -g wscat)
wscat -c ws://localhost:8000/ws/notifications/

# Check if Redis channel layer is working
python manage.py shell
>>> from channels.layers import get_channel_layer
>>> layer = get_channel_layer()
>>> print(layer)
```

### CSRF Debugging

```bash
# Check current CSRF_TRUSTED_ORIGINS
python manage.py shell -c "from django.conf import settings; print(settings.CSRF_TRUSTED_ORIGINS)"

# Check CSRF cookie settings
python manage.py shell -c "from django.conf import settings; print('CSRF_COOKIE_SECURE:', settings.CSRF_COOKIE_SECURE); print('SESSION_COOKIE_SECURE:', settings.SESSION_COOKIE_SECURE)"

# Check ALLOWED_HOSTS
python manage.py shell -c "from django.conf import settings; print(settings.ALLOWED_HOSTS)"

# Test CSRF token generation
python manage.py shell
>>> from django.middleware.csrf import get_token
>>> from django.test import RequestFactory
>>> factory = RequestFactory()
>>> request = factory.get('/')
>>> token = get_token(request)
>>> print(token)
```

**Common CSRF Issues and Fixes:**

1. **CSRF_TRUSTED_ORIGINS mismatch**: Ensure your frontend URL is in `CSRF_TRUSTED_ORIGINS`
2. **Cookie security settings**: In local dev, ensure `CSRF_COOKIE_SECURE=False` and `SESSION_COOKIE_SECURE=False`
3. **Missing csrf_token**: Ensure forms include `{% csrf_token %}` template tag
4. **Browser cookies disabled**: Ensure browser accepts cookies from localhost
5. **HTTP vs HTTPS**: CSRF tokens are tied to the protocol - don't mix HTTP and HTTPS

**API CSRF Handling in Local Development:**

For local development, API endpoints (`/api/*`) are automatically exempt from CSRF verification via `CSRFExemptMiddleware`. This is a development convenience - production should use proper CSRF handling with authentication tokens.

If you still get CSRF errors on API endpoints:
- Ensure the middleware is loaded in `pwaninet/settings/local.py`
- Restart the Django server after configuration changes
- For production, use TokenAuthentication or SessionAuthentication with proper CSRF tokens

## Common Mistakes

### 1. Mixing Docker + Local DB_HOST

**Wrong**:
```bash
# Using .env.local with DB_HOST=db (Docker service name)
DB_HOST=db  # This won't work from host machine
```

**Correct**:
```bash
# .env.local should use localhost
DB_HOST=localhost
```

### 2. Running Multiple Django Servers

**Wrong**:
```bash
# Terminal 1
python manage.py runserver

# Terminal 2
uvicorn pwaninet.asgi:application --reload
# Both trying to use port 8000
```

**Correct**:
```bash
# Only run one at a time
# Use runserver for REST API only
# Use uvicorn for WebSockets (includes REST API)
```

### 3. Using runserver for WebSockets

**Wrong**:
```bash
# Django runserver doesn't support WebSockets properly
python manage.py runserver
# Then trying to connect to ws://localhost:8000/ws/notifications/
```

**Correct**:
```bash
# Use uvicorn for WebSocket support
uvicorn pwaninet.asgi:application --reload
```

### 4. Duplicate .env Keys

**Wrong**:
```bash
# .env.local
DB_NAME=pwaninet_db
DB_NAME=pwaninet  # Duplicate key - second one overwrites first
```

**Correct**:
```bash
# Each key appears only once
DB_NAME=pwaninet_db
DB_USER=postgres
DB_PASSWORD=postgres
```

### 5. Not Loading Environment Variables

**Wrong**:
```bash
# Django can't find .env.local
python manage.py runserver
# Settings use defaults instead of .env values
```

**Correct**:
```bash
# Ensure django-environ or python-dotenv is installed
# The project settings/__init__.py loads .env.local automatically
# Verify by checking: python manage.py shell -c "import os; print(os.environ.get('DB_NAME'))"
```

### 6. Docker Services Not Running

**Wrong**:
```bash
# Trying to run Django without starting Docker services
python manage.py runserver
# Fails with connection refused to PostgreSQL/Redis
```

**Correct**:
```bash
# Always start Docker services first
docker compose up -d db redis
# Then run Django
python manage.py runserver
```

### 7. Wrong Environment File for Mode

**Wrong**:
```bash
# Running Django in Docker but using .env.local
docker compose up web  # web service uses .env.docker
# But you configured .env.local with localhost
```

**Correct**:
```bash
# For local dev: use .env.local, run Django on host
# For Docker: use .env.docker, run Django in containers
# Never mix them
```

## Quick Reference Commands

```bash
# Start everything (local dev)
docker compose up -d db redis
python manage.py migrate
python manage.py runserver

# Start with WebSockets
docker compose up -d db redis
uvicorn pwaninet.asgi:application --reload

# Stop everything
docker compose down

# View logs
docker compose logs -f

# Reset database (WARNING: deletes data)
docker compose down -v
docker compose up -d db redis
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run tests
python manage.py test

# Collect static files
python manage.py collectstatic
```

## Troubleshooting Checklist

If something isn't working:

1. **Are Docker services running?**
   ```bash
   docker compose ps
   ```

2. **Are ports available?**
   ```bash
   lsof -i :8000
   lsof -i :5432
   lsof -i :6379
   ```

3. **Is the correct .env file being used?**
   ```bash
   cat .env.local  # or .env.docker
   ```

4. **Can Django connect to the database?**
   ```bash
   python manage.py dbshell
   ```

5. **Is Redis accessible?**
   ```bash
   docker exec -it pwaninet-redis-1 redis-cli PING
   ```

6. **Are you using the right server?**
   - REST API only: `python manage.py runserver`
   - WebSockets: `uvicorn pwaninet.asgi:application --reload`

7. **Check Django settings**
   ```bash
   python manage.py check
   ```

## Additional Resources

- Django Channels documentation: https://channels.readthedocs.io/
- uvicorn documentation: https://www.uvicorn.org/
- Docker Compose documentation: https://docs.docker.com/compose/
