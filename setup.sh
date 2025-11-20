#!/bin/bash

echo "Configurando Skynet en VM Linux..."

if ! dpkg -l | grep -q python3; then
    echo "Instalando dependencias del sistema..."
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv nodejs npm git curl
else
    echo "Dependencias del sistema ya instaladas."
fi

if ! command -v ollama &> /dev/null; then
    echo "Instalando Ollama..."
    curl -fsSL https://ollama.ai/install.sh | sh
else
    echo "Ollama ya instalado."
fi

if [ ! -d "venv" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv venv
else
    echo "Entorno virtual ya existe."
fi

source venv/bin/activate

echo "Verificando dependencias Python..."
pip install -r requirements.txt

if ! pip list | grep -q playwright; then
    echo "Instalando Playwright..."
    pip install playwright
    playwright install --with-deps chromium
fi

cd backend
echo "Inicializando vault de credenciales..."
python << 'PYEOF'
import sys
import os
sys.path.append('..')
from services.tools import vault
from dotenv import load_dotenv

load_dotenv('.env')
sudo_user = os.getenv('SUDO_USER', '')
sudo_pwd = os.getenv('SUDO_PASSWORD', '')

if sudo_user:
    vault.set_credential('sudo_user', sudo_user)
    print(f"Stored sudo_user: {sudo_user}")
if sudo_pwd:
    vault.set_credential('sudo_password', sudo_pwd)
    print("Stored sudo_password")
PYEOF

cd ..

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

cat > ~/Skynet/run.sh << 'EOF'
#!/bin/bash
cd ~/Skynet

cleanup() {
    echo "Deteniendo procesos..."
    kill $UVICORN_PID 2>/dev/null
    pkill -P $$ 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

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
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --log-level info &
UVICORN_PID=$!
wait $UVICORN_PID
EOF
chmod +x ~/Skynet/run.sh

if ! pgrep -x "ollama" > /dev/null; then
    echo "Iniciando Ollama..."
    ollama serve &
    sleep 5
else
    echo "Ollama ya corriendo."
fi

if ! ollama list | grep -q "qwen2.5-coder:7b"; then
    echo "Descargando modelo qwen2.5-coder:7b (FAST/CODING/REASONING)..."
    ollama pull qwen2.5-coder:7b
else
    echo "Modelo qwen2.5-coder:7b ya disponible."
fi

echo "Configuración completa. Ejecuta: ~/Skynet/run.sh"