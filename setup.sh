#!/bin/bash

echo "Configurando Skynet en VM Linux..."

# Instalar dependencias del sistema
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nodejs npm git curl

# Instalar Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias Python en venv
cd backend
pip install -r requirements.txt
cd ..

# Construir frontend
cd frontend
echo "Instalando dependencias de Node.js..."
npm install
if [ ! -d "node_modules" ]; then
    echo "Error: npm install falló"
    exit 1
fi
echo "Construyendo frontend..."
npm run build
if [ ! -d "dist" ]; then
    echo "Error: npm run build falló"
    exit 1
fi
cd ..

# Crear script de ejecución en ~/Skynet
cat > ~/Skynet/run.sh << 'EOF'
#!/bin/bash
cd ~/Skynet

# Verificar que el frontend esté construido
if [ ! -d "frontend/dist" ]; then
    echo "Construyendo frontend..."
    cd frontend
    npm install
    npm run build
    cd ..
    if [ ! -d "frontend/dist" ]; then
        echo "Error: No se pudo construir el frontend"
        exit 1
    fi
fi

source venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000
EOF
chmod +x ~/Skynet/run.sh

# Iniciar Ollama y descargar modelo
ollama serve &
sleep 5
ollama pull llama3:8b-instruct

echo "Configuración completa. Ejecuta: ~/Skynet/run.sh"