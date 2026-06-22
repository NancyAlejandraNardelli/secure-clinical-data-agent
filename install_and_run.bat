@echo off
echo ===================================================
echo Clinical AI Agent - Kaggle Setup (Windows)
echo ===================================================

echo [1/4] Comprobando archivo .env...
if not exist .env (
    copy .env.example .env >nul
    echo Se ha creado el archivo .env a partir de .env.example
) else (
    echo Archivo .env ya existe.
)

echo [2/4] Creando entorno virtual (.venv)...
python -m venv .venv
if errorlevel 1 (
    echo Error: Asegurate de tener Python instalado y agregado al PATH.
    pause
    exit /b
)

echo [3/4] Activando entorno virtual e instalando dependencias...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo [4/4] Instalacion completada con exito.
echo.
echo ===================================================
echo IMPORTANTE:
echo Abre el archivo .env y configura tu GEMINI_API_KEY
echo para usar el modo Kaggle (Fallback con CSV).
echo.
echo Para iniciar el agente, simplemente ejecuta:
echo call .venv\Scripts\activate.bat
echo python main.py
echo ===================================================
echo.
pause
