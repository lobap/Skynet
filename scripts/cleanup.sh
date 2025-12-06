#!/bin/bash
echo "🧹 Cleaning up residual files..."

# Remove local venv if exists
if [ -d "venv" ]; then
    echo "Removing venv..."
    rm -rf venv
fi

# Remove __pycache__
echo "Removing __pycache__..."
find . -type d -name "__pycache__" -exec rm -rf {} +

# Remove old scripts
if [ -f "fix_memory.sh" ]; then
    rm fix_memory.sh
fi

echo "✅ Cleanup complete. Ready for Docker."
