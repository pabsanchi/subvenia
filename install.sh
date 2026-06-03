#!/bin/bash
set -e

# Colores para la salida en consola
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}             🚀 INSTALADOR AUTOMATIZADO - SUBVENIA                    ${NC}"
echo -e "${CYAN}======================================================================${NC}\n"

# 1. Comprobar si Python3 está instalado
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: python3 no está instalado en este sistema.${NC}"
    echo "Por favor, instala Python 3 y vuelve a intentarlo."
    exit 1
fi

echo -e "${GREEN}✅ Python3 detectado.${NC}"

# 2. Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⏳ Creando entorno virtual (venv) en la raíz del proyecto...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✅ Entorno virtual creado.${NC}"
else
    echo -e "${GREEN}✅ Entorno virtual ya existe.${NC}"
fi

# 3. Activar el entorno virtual e instalar dependencias
echo -e "${YELLOW}⏳ Instalando dependencias desde requirements.txt...${NC}"
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt
echo -e "${GREEN}✅ Dependencias instaladas correctamente.${NC}"

# 4. Configurar variables de entorno
echo -e "\n${CYAN}--- Configuración de Entorno ---${NC}"
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⏳ Archivo .env no encontrado. Creando a partir de la plantilla...${NC}"
    cp .env.example .env
    echo -e "${RED}⚠️  ¡ATENCIÓN! Se ha creado un archivo .env en la raíz.${NC}"
    echo -e "${RED}El proyecto NO funcionará si no configuras las variables GEMINI_API_KEY y MONGO_URI dentro de este archivo.${NC}"
else
    echo -e "${GREEN}✅ Archivo .env existente detectado.${NC}"
fi

# 5. Mensajes Finales y Advertencias
echo -e "\n${CYAN}======================================================================${NC}"
echo -e "${GREEN}🎉 Instalación completada con éxito. 🎉${NC}"
echo -e "${CYAN}======================================================================${NC}\n"

echo -e "${YELLOW}⚠️  PASOS SIGUIENTES Y ADVERTENCIAS:${NC}"
echo -e "1. Edita el archivo ${CYAN}.env${NC} y coloca tus credenciales (si no lo has hecho ya)."
echo -e "2. ${RED}¡IMPORTANTE!${NC} Si tu base de datos de Mongo no tiene datos, el bot de ayuda NO podrá responder a las preguntas."
echo -e "   Para ingerir datos, ejecuta el scraper y la ingesta así:"
echo -e "     ${CYAN}source venv/bin/activate${NC}"
echo -e "     ${CYAN}python modules/modulo1-scraper/src/analyze_gemini.py${NC}"
echo -e "     ${CYAN}python modules/modulo2-db/src/ingest.py${NC}"
echo -e "3. Una vez que tengas datos, puedes levantar la aplicación con:"
echo -e "     ${CYAN}./start_frontEnd.sh${NC}\n"
