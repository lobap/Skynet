#!/bin/bash

echo "🚀 Initializing Skynet Hive-Mind Protocol..."

# 1. Check if Ollama is running on host
if curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "✅ Ollama is online."
else
    echo "❌ Ollama is NOT running on localhost:11434."
    echo "Please start Ollama and try again."
    exit 1
fi

# 2. Pull required models (Hive-Mind) - Smart Check
echo "🧠 Synchronizing Neural Networks..."

check_and_pull() {
    MODEL=$1
    if ollama list | grep -q "$MODEL"; then
        echo "   - ✅ $MODEL already exists."
    else
        echo "   - ⬇️ Pulling $MODEL..."
        ollama pull "$MODEL"
    fi
}

check_and_pull "llama3.2:latest"
check_and_pull "deepseek-r1:8b"
check_and_pull "qwen2.5-coder:7b"

# 3. Start Docker Environment
echo "🐳 Deploying Containerized Infrastructure..."
cd "$(dirname "$0")/.." || exit
docker-compose -f docker/docker-compose.yml up --build
