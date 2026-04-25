# Pwaninet Setup Guide

This guide covers the complete setup process for Pwaninet, including Docker, PostgreSQL, and Python dependencies installation for both Windows and Linux,read it when your machine is giving you headache or use AI to set up everything it depends whether you are oline or offline.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Cloning the Repository](#cloning-the-repository)
3. [Docker Installation](#docker-installation)
4. [PostgreSQL Installation](#postgresql-installation)
5. [Project Setup](#project-setup)
6. [Running the Application](#running-the-application)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you begin, ensure you have:

- **Git** - For cloning the repository
- **Python 3.11+** - For running the application
- **Docker & Docker Compose** - For containerized setup (recommended)
- **PostgreSQL** - For local database (if not using Docker)
- **Redis** - For caching (if not using Docker)

---

## Cloning the Repository

### Clone from GitHub

```bash
# Clone the repository
git clone <repository-url>
cd pwaninet
```

Or if you already have access:

```bash
# Navigate to the project directory
cd /path/to/pwaninet
```

---

## Docker Installation

### Windows

#### Option 1: Docker Desktop (Recommended)

1. Download Docker Desktop for Windows from [docker.com](https://www.docker.com/products/docker-desktop/)
2. Run the installer and follow the setup wizard
3. Restart your computer when prompted
4. Open Docker Desktop and ensure it's running
5. Verify installation:

```powershell
docker --version
docker-compose --version
```

#### Option 2: Using WSL2

1. Enable WSL2 in PowerShell (Admin):

```powershell
wsl --install
```

2. Restart your computer
3. Install Docker Desktop for Windows (includes WSL2 support)
4. Verify installation:

```powershell
docker --version
```

### Linux (Ubuntu/Debian)

#### Install Docker

```bash
# Update package index
sudo apt update

# Install prerequisites
sudo apt install -y ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up the repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add your user to the docker group (optional, to avoid sudo)
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker compose version
```

#### Alternative: Install via Snap

```bash
sudo snap install docker
```

### Linux (Other Distributions)

For Fedora, CentOS, RHEL, or other distributions, follow the official Docker documentation:
https://docs.docker.com/engine/install/

---

## PostgreSQL Installation

### Option 1: Using Docker (Recommended)

If you're using Docker Compose, PostgreSQL is already included in the setup. Skip to [Project Setup](#project-setup).

### Option 2: Local Installation

### Windows

1. Download PostgreSQL installer from [postgresql.org](https://www.postgresql.org/download/windows/)
2. Run the installer and follow the setup wizard
3. Remember the password you set for the `postgres` user
4. Ensure the PostgreSQL service is running:
   - Open Services (Win+R, type `services.msc`)
   - Find `postgresql-x64-XX` service
   - Ensure it's set to "Running"

5. Verify installation:

```powershell
psql --version
```

### Linux (Ubuntu/Debian)

```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Verify installation
psql --version
```

### Linux (macOS with Homebrew)

```bash
# Install PostgreSQL
brew install postgresql

# Start PostgreSQL service
brew services start postgresql

# Verify installation
psql --version
```

---

## Project Setup

### Step 1: Create Environment Variables

Create a `.env` file in the project root:

#### For Docker Setup

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

# Django Settings
SECRET_KEY=your-secret-key-here-change-this
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

#### For Local Development (without Docker)

```env
# Database (PostgreSQL for local)
DB_NAME=pwaninet
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432

# Redis (for caching - local)
REDIS_URL=redis://localhost:6379/1

# Celery (local)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Django Settings
SECRET_KEY=your-secret-key-here-change-this
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Step 2: Install Python Dependencies

#### Windows

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Upgrade pip
python -m pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
```

#### Linux/macOS

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
python -m pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
```

### Step 3: Create Database (Local Setup Only)

If you're using Docker, skip this step - the database is created automatically.

#### Windows

```powershell
# Open psql as postgres user
psql -U postgres

# In psql, run:
CREATE DATABASE pwaninet;
CREATE USER pwaninet WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE pwaninet TO pwaninet;
\q
```

#### Linux

```bash
# Switch to postgres user and enter psql
sudo -u postgres psql

# In psql, run:
CREATE DATABASE pwaninet;
CREATE USER pwaninet WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE pwaninet TO pwaninet;
\q
```

### Step 4: Run Database Migrations

#### With Docker

```bash
# Build and start services
docker compose up --build -d

# Run migrations
docker compose exec web python manage.py migrate
```

#### Local Development

```bash
# Activate virtual environment (if not already active)
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

# Run migrations
python manage.py migrate
```

### Step 5: Create Superuser (Optional)

#### With Docker

```bash
docker compose exec web python manage.py createsuperuser
```

#### Local Development

```bash
python manage.py createsuperuser
```

---

## Running the Application

### Option 1: Using Docker (Recommended)

#### Windows & Linux

```bash
# Start all services in detached mode
docker compose up -d

# View logs
docker compose logs -f web

# Stop services
docker compose down

# Stop and remove volumes (clean slate)
docker compose down -v
```

**Services started:**
- **db**: PostgreSQL 15 database (port 5432)
- **redis**: Redis 7 for caching (port 6379)
- **web**: Django application (port 8000)
- **celery**: Celery worker for background tasks
- **celery-beat**: Celery beat scheduler for periodic tasks

**Access the application:**
- Web App: http://localhost:8000
- Admin Panel: http://localhost:8000/admin

### Option 2: Local Development

#### Windows

```powershell
# Activate virtual environment
venv\Scripts\activate

# Start Django development server
python manage.py runserver

# In a separate terminal (activate venv first):
# Start Celery worker
celery -A pwaninet worker -l info

# In another terminal (activate venv first):
# Start Celery beat
celery -A pwaninet beat -l info
```

#### Linux/macOS

```bash
# Activate virtual environment
source venv/bin/activate

# Start Django development server
python manage.py runserver

# In a separate terminal (activate venv first):
# Start Celery worker
celery -A pwaninet worker -l info

# In another terminal (activate venv first):
# Start Celery beat
celery -A pwaninet beat -l info
```

---

## Troubleshooting

### Docker Issues

#### Issue: "docker: command not found"

**Solution:** Docker is not installed or not in PATH. Refer to the [Docker Installation](#docker-installation) section.

#### Issue: "Permission denied" when running docker commands

**Linux Solution:**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

#### Issue: Port already in use (8000, 5432, 6379)

**Linux/macOS:**
```bash
# Find process using the port
lsof -i :8000

# Kill the process
kill -9 <PID>
```

**Windows:**
```powershell
# Find process using the port
netstat -ano | findstr :8000

# Kill the process
taskkill /PID <PID> /F
```

### PostgreSQL Issues

#### Issue: "Connection refused" to PostgreSQL

**Docker:**
- Ensure db service is running: `docker compose ps`
- Check logs: `docker compose logs db`
- Verify `.env` has `DB_HOST=db`

**Local:**
- Ensure PostgreSQL is running:
  - Linux: `sudo systemctl status postgresql`
  - Windows: Check Services for PostgreSQL
- Verify `DB_HOST=localhost` in `.env`

#### Issue: "FATAL: database "pwaninet" does not exist"

**Solution:** Create the database following [Step 3](#step-3-create-database-local-setup-only)

### Python Issues

#### Issue: "ModuleNotFoundError: No module named 'xxx'"

**Solution:** Ensure you've installed all requirements:

```bash
# Activate virtual environment first
# Then:
pip install -r requirements.txt
```

#### Issue: Virtual environment not activating

**Windows:**
```powershell
# Make sure you're in the project directory
cd path\to\pwaninet
venv\Scripts\activate
```

**Linux/macOS:**
```bash
# Make sure you're in the project directory
cd /path/to/pwaninet
source venv/bin/activate
```

### Redis Issues

#### Issue: Redis connection errors

**Docker:**
- Ensure redis service is running: `docker compose ps`
- Check logs: `docker compose logs redis`
- Verify `REDIS_URL=redis://redis:6379/1` in `.env`

**Local:**
- Ensure Redis is running:
  - Linux: `sudo systemctl status redis-server`
  - macOS: `brew services list`
- Verify `REDIS_URL=redis://localhost:6379/1` in `.env`

### Migration Issues

#### Issue: Migration errors

**Solution:** Reset migrations (development only):

```bash
# With Docker
docker compose exec web python manage.py migrate --run-syncdb

# Local
python manage.py migrate --run-syncdb
```

For a clean slate (WARNING: deletes data):

```bash
# With Docker
docker compose down -v
docker compose up --build -d
docker compose exec web python manage.py migrate

# Local
# Delete database and recreate
sudo -u postgres psql -c "DROP DATABASE pwaninet;"
sudo -u postgres psql -c "CREATE DATABASE pwaninet;"
python manage.py migrate
```

---

## Quick Reference Commands

### Docker Commands

```bash
# Build and start
docker compose up --build -d

# View logs
docker compose logs -f web

# Stop services
docker compose down

# Restart services
docker compose restart

# Execute command in container
docker compose exec web python manage.py <command>

# Create superuser
docker compose exec web python manage.py createsuperuser

# Run migrations
docker compose exec web python manage.py migrate

# Collect static files
docker compose exec web python manage.py collectstatic --noinput
```

### Local Development Commands

```bash
# Activate virtual environment
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

# Run server
python manage.py runserver

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic

# Start Celery worker
celery -A pwaninet worker -l info

# Start Celery beat
celery -A pwaninet beat -l info
```

---

## Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [Celery Documentation](https://docs.celeryq.dev/)

---

## Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review Docker logs: `docker compose logs`
3. Check Django debug output for errors
4. Contact the development team

---

**Happy Bruvs! **
