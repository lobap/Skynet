#!/bin/bash
echo "Iniciando protocolo de emergencia de memoria..."

if systemctl is-active --quiet ollama; then
    echo "Deteniendo servicio Ollama..."
    sudo systemctl stop ollama
fi

echo "Limpiando caches..."
sync; echo 3 | sudo tee /proc/sys/vm/drop_caches

echo "Reiniciando Ollama..."
sudo systemctl start ollama
sleep 5

echo "Descargando modelo Nano (qwen2.5-coder:1.5b)..."
ollama pull qwen2.5-coder:1.5b

echo "Memory cleared. Nano model ready."
