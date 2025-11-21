#!/bin/bash
set -e

echo "Starting Skynet Container..."

# Build Frontend
echo "Building Frontend..."
if [ -d "frontend" ]; then
    cd frontend
    if [ ! -d "node_modules" ]; then
        echo "Installing frontend dependencies..."
        npm install
    fi
    echo "Building Astro project..."
    npm run build
    cd ..
else
    echo "Frontend directory not found!"
fi

# Start Backend
echo "Starting Backend..."
# We use --host 0.0.0.0 to make it accessible outside the container
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
