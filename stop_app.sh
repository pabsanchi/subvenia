#!/bin/bash

echo "======================================"
echo "🛑 DETENIENDO SERVICIOS DE SUBVENIA"
echo "======================================"

echo ""
echo "Deteniendo interfaz de Streamlit..."
pkill -f "streamlit run" || echo "Streamlit no estaba en ejecución."

echo ""
echo "Deteniendo el servicio de Ollama..."
sudo systemctl stop ollama || echo "No se pudo detener Ollama (probablemente no estaba en ejecución o no tienes permisos)."

echo ""
echo "✅ Todos los servicios han sido detenidos."
