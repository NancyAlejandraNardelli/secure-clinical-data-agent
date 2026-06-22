#!/bin/bash
echo "==================================================="
echo "Clinical AI Agent - Kaggle Setup (Linux/Mac)"
echo "==================================================="

echo "[1/4] Comprobando archivo .env..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Se ha creado el archivo .env a partir de .env.example"
else
    echo "Archivo .env ya existe."
fi

echo "[2/4] Creando entorno virtual (.venv)..."
python3 -m venv .venv
if [ $? -ne 0 ]; then
    echo "Error: Asegúrate de tener Python 3 instalado."
    exit 1
fi

echo "[3/4] Activando entorno virtual e instalando dependencias..."
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "[4/4] Instalación completada con éxito."
echo ""
echo "==================================================="
echo "IMPORTANTE:"
echo "Abre el archivo .env y configura tu GEMINI_API_KEY"
echo "para usar el modo Kaggle (Fallback con CSV)."
echo ""
echo "Para iniciar el agente, simplemente ejecuta:"
echo "source .venv/bin/activate"
echo "python main.py"
echo "==================================================="
echo ""
