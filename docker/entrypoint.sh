#!/bin/bash
set -e

echo "Starting Skynet Container..."

# Smart Frontend Build
echo "Checking Frontend..."
if [ -d "frontend" ]; then
    cd frontend
    # Check if dist/index.html exists (Verification of successful build)
    echo "Building Frontend..."
    echo "Installing frontend dependencies..."
    npm install
    echo "Building Astro project..."
    npm run build
    cd ..
else
    echo "Frontend directory not found!"
fi

# Start Backend
echo "Starting Backend..."
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
