#!/bin/bash

# Pwaninet Environment Setup Script
# This script helps switch between local and Docker development modes

set -e

echo "Pwaninet Environment Setup"
echo "=========================="

# Function to copy environment file
copy_env() {
    local mode=$1
    echo "Setting up $mode environment..."
    
    # Backup current .env if it exists
    if [ -f .env ]; then
        cp .env .env.backup
        echo "Current .env backed up to .env.backup"
    fi
    
    # Copy the appropriate environment file
    cp ".env.$mode" .env
    echo "Environment configured for $mode mode"
    
    # Show current configuration
    echo ""
    echo "Current configuration:"
    echo "DB_HOST=$(grep DB_HOST .env)"
    echo "REDIS_HOST=$(grep REDIS_HOST .env)"
    echo "REDIS_URL=$(grep REDIS_URL .env)"
    echo "ENV_MODE=$(grep ENV_MODE .env)"
}

# Main logic
case "${1:-}" in
    "local")
        copy_env "local"
        echo ""
        echo "To start local development:"
        echo "  1. Make sure PostgreSQL and Redis are running locally"
        echo "  2. Run: python manage.py runserver"
        ;;
    "docker")
        copy_env "docker"
        echo ""
        echo "To start Docker development:"
        echo "  1. Run: docker-compose up -d"
        echo "  2. The application will be available at http://localhost:8000"
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [local|docker|help]"
        echo ""
        echo "Commands:"
        echo "  local   - Configure for local development (localhost services)"
        echo "  docker  - Configure for Docker development (Docker services)"
        echo "  help    - Show this help message"
        ;;
    "")
        echo "Error: Please specify a mode"
        echo "Usage: $0 [local|docker|help]"
        exit 1
        ;;
    *)
        echo "Error: Unknown mode '$1'"
        echo "Usage: $0 [local|docker|help]"
        exit 1
        ;;
esac
