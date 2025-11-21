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

# 2. Pull required models (Hive-Mind)
echo "🧠 Synchronizing Neural Networks (Pulling Models)..."
echo "   - Pulling Coordinator (llama3.1:8b)..."
ollama pull llama3.1:8b
echo "   - Pulling Architect (deepseek-r1:8b)..."
ollama pull deepseek-r1:8b
echo "   - Pulling Engineer (qwen2.5-coder:14b)..."
ollama pull qwen2.5-coder:14b

# 3. Start Docker Environment
echo "🐳 Deploying Containerized Infrastructure..."
docker-compose up --build
