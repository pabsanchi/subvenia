#!/bin/bash
set -e

echo "======================================"
echo "🚀 INICIANDO SUBVENIA (RAG + Frontend)"
echo "======================================"
echo ""

sudo systemctl start ollama

echo "Paso 1: Verificando y calentando el modelo en Ollama..."
# Asegurarse de que el servicio está activo (puede requerir sudo, pero asumimos que ya está)
# Lanzamos el script de warmup
PYTHONPATH=. python modules/modulo3-rag/src/warmup_ollama.py

echo ""
echo "Paso 2: Levantando la interfaz gráfica (Streamlit)..."
PYTHONPATH=. streamlit run modules/modulo4-frontend/src/app.py
