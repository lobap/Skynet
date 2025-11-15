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
npm install
npm run build
cd ..

# Crear script de ejecución en ~/Skynet
cat > ~/Skynet/run.sh << 'EOF'
#!/bin/bash
cd ~/Skynet
source venv/bin/activate
python backend/main.py
EOF
chmod +x ~/Skynet/run.sh

# Iniciar Ollama y descargar modelo
ollama serve &
sleep 5
ollama pull llama3:8b-instruct

echo "Configuración completa. Ejecuta: ~/Skynet/run.sh"