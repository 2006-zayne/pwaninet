# PwaniNet Development Setup Guide

This guide explains how to set up and test PwaniNet for development, both with Docker and for offline/local development.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Docker Setup (Recommended)](#docker-setup-recommended)
3. [Local Development Setup (Offline)](#local-development-setup-offline)
4. [Running the Application](#running-the-application)
5. [Testing the Application](#testing-the-application)
6. [Common Issues & Solutions](#common-issues--solutions)

---

## Prerequisites

- Python 3.12+
- Docker & Docker Compose (for Docker setup)
- PostgreSQL (for local setup)
- Redis (for local setup)
- Git

---

## Docker Setup (Recommended)

### 1. Clone the Repository

```bash
git clone <repository-url>
cd pwaninet
```

### 2. Configure Environment Variables

The `.env` file is already configured for Docker:

```env
# Database (PostgreSQL for Docker)
DB_NAME=pwaninet
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432

# Redis (for caching - Docker service)
REDIS_URL=redis://redis:6379/1

# Celery (Docker service)
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

### 3. Build and Start Services

```bash
# Build and start all services
docker-compose up --build

# Or start in detached mode
docker-compose up -d --build
```

This will start:
- **db**: PostgreSQL 15 database
- **redis**: Redis 7 for caching
- **web**: Django application
- **celery**: Celery worker
- **celery-beat**: Celery beat scheduler

### 4. Run Migrations

```bash
docker-compose exec web python manage.py migrate
```

### 5. Create Superuser (Optional)

```bash
docker-compose exec web python manage.py createsuperuser
```

### 6. Access the Application

- **Web App**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin

---

## Local Development Setup (Offline)

For offline development without Docker, you need to run PostgreSQL and Redis locally.

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python packages
pip install -r requirements.txt
```

### 2. Install PostgreSQL

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**macOS (with Homebrew):**
```bash
brew install postgresql
brew services start postgresql
```

**Windows:** Download from [postgresql.org](https://www.postgresql.org/download/windows/)

### 3. Install Redis

**Ubuntu/Debian:**
```bash
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**macOS (with Homebrew):**
```bash
brew install redis
brew services start redis
```

**Windows:** Download from [redis.io](https://redis.io/download)

### 4. Create Database

```bash
# Switch to postgres user
sudo -u postgres psql

# In psql:
CREATE DATABASE pwaninet;
CREATE USER pwaninet WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE pwaninet TO pwaninet;
\q
```

### 5. Configure Environment for Local Development

Create or update `.env` file:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (PostgreSQL for local)
DB_NAME=pwaninet
DB_USER=pwaninet
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# Redis (for caching - local)
REDIS_URL=redis://localhost:6379/1

# Celery (local)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

### 6. Run Migrations

```bash
python manage.py migrate
```

### 7. Create Superuser

```bash
python manage.py createsuperuser
```

---

## Running the Application

### With Docker

```bash
# Start all services
docker-compose up

# View logs
docker-compose logs -f web

# Stop services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

### Local Development

```bash
# Start Django development server
python manage.py runserver

# Start Celery worker (in separate terminal)
celery -A pwaninet worker -l info

# Start Celery beat (in another terminal)
celery -A pwaninet beat -l info
```

---

## Testing the Application

### 1. Basic Functionality Tests

#### Test Home Page
```bash
# With Docker
curl http://localhost:8000/

# Local
curl http://127.0.0.1:8000/
```

#### Test Admin Panel
1. Navigate to http://localhost:8000/admin
2. Login with superuser credentials
3. Verify you can access the admin interface

#### Test User Registration
1. Navigate to http://localhost:8000/core/register/
2. Fill in registration form
3. Verify account creation

#### Test Login/Logout
1. Navigate to http://localhost:8000/accounts/login/
2. Login with created user
3. Verify redirect to home page
4. Test logout functionality

### 2. API Testing

#### Test API Endpoints
```bash
# Test posts endpoint
curl http://localhost:8000/api/posts/

# Test with authentication (if needed)
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/posts/
```

### 3. Database Connection Tests

#### With Docker
```bash
# Connect to PostgreSQL container
docker-compose exec db psql -U postgres -d pwaninet

# In psql, test connection
\dt  # List tables
SELECT * FROM auth_user;  # Check users table
\q
```

#### Local
```bash
psql -U pwaninet -d pwaninet

# In psql
\dt
SELECT * FROM auth_user;
\q
```

### 4. Redis Connection Tests

#### With Docker
```bash
# Connect to Redis container
docker-compose exec redis redis-cli

# Test
PING  # Should return PONG
\q
```

#### Local
```bash
redis-cli

# Test
PING  # Should return PONG
\q
```

### 5. Cache Functionality Tests

```bash
# Python shell
python manage.py shell

# Test cache
from django.core.cache import cache
cache.set('test_key', 'test_value', 60)
cache.get('test_key')  # Should return 'test_value'
exit()
```

---

## Common Issues & Solutions

### Issue 1: "Connection refused" to PostgreSQL

**Docker:**
- Ensure db service is running: `docker-compose ps`
- Check logs: `docker-compose logs db`
- Verify `.env` has `DB_HOST=db`

**Local:**
- Ensure PostgreSQL is running: `sudo systemctl status postgresql`
- Verify `DB_HOST=localhost` in `.env`
- Check if database exists: `psql -U postgres -l`

### Issue 2: Redis connection errors

**Docker:**
- Ensure redis service is running: `docker-compose ps`
- Check logs: `docker-compose logs redis`
- Verify `REDIS_URL=redis://redis:6379/1` in `.env`

**Local:**
- Ensure Redis is running: `sudo systemctl status redis-server`
- Verify `REDIS_URL=redis://localhost:6379/1` in `.env`
- Test with `redis-cli ping`

### Issue 3: Migration errors

```bash
# Reset migrations (development only)
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete

# Re-run migrations
python manage.py makemigrations
python manage.py migrate
```

### Issue 4: Static files not loading

```bash
# Collect static files
python manage.py collectstatic

# For Docker, ensure static volume is mounted
docker-compose down
docker-compose up --build
```

### Issue 5: Docker Compose command not found

If `docker compose` doesn't work, try:
```bash
docker-compose up --build  # With hyphen
```

Or install Docker Compose V2:
```bash
# Linux
sudo apt-get update
sudo apt-get install docker-compose-plugin
```

### Issue 6: Port already in use

```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port in docker-compose.yml
ports:
  - "8001:8000"
```

---

## Switching Between Docker and Local Development

### From Docker to Local

1. Stop Docker: `docker-compose down`
2. Update `.env`:
   - Change `DB_HOST=db` to `DB_HOST=localhost`
   - Change `REDIS_URL=redis://redis:6379/1` to `REDIS_URL=redis://localhost:6379/1`
3. Ensure local PostgreSQL and Redis are running
4. Run: `python manage.py runserver`

### From Local to Docker

1. Stop local services
2. Update `.env`:
   - Change `DB_HOST=localhost` to `DB_HOST=db`
   - Change `REDIS_URL=redis://localhost:6379/1` to `REDIS_URL=redis://redis:6379/1`
3. Run: `docker-compose up --build`

---

## Development Workflow

### Recommended Workflow

1. **Feature Development**
   ```bash
   # Create feature branch
   git checkout -b feature/your-feature
   
   # Make changes
   # Test locally
   python manage.py runserver
   ```

2. **Testing**
   ```bash
   # Run tests (if test suite exists)
   python manage.py test
   
   # Check for issues
   python manage.py check
   ```

3. **Migrations**
   ```bash
   # Create migrations after model changes
   python manage.py makemigrations
   
   # Apply migrations
   python manage.py migrate
   ```

4. **Commit**
   ```bash
   git add .
   git commit -m "Your commit message"
   git push origin feature/your-feature
   ```

---

## Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)

---

## Support

For issues or questions:
1. Check the [Common Issues](#common-issues--solutions) section
2. Review Docker logs: `docker-compose logs`
3. Check Django debug output for errors
