#!/bin/bash

# Pwaninet Server Script
# Starts the Django application using Docker Compose

echo "Starting Pwaninet server with Docker Compose..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Start the services
docker compose up web

# Note: To run in background, use: docker compose up -d web
# To view logs: docker compose logs -f web
# To stop: docker compose down
