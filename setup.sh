#!/bin/bash

echo "Configurando Skynet en VM Linux..."

# Instalar dependencias del sistema
sudo apt update
sudo apt install -y python3 python3-pip nodejs npm git curl

# Instalar Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Iniciar Ollama y descargar modelo
ollama serve &
sleep 5
ollama pull llama3:8b-instruct

# Instalar dependencias Python
cd backend
pip3 install -r requirements.txt

# Construir frontend
cd ../frontend
npm install
npm run build

# Volver al root
cd ..

echo "Configuración completa. Ejecuta: python3 backend/main.py"