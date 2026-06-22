# 🏥 Secure Clinical Data Agent (Google ADK & MCP)

![Kaggle](https://img.shields.io/badge/Kaggle-20BEFF?style=for-the-badge&logo=Kaggle&logoColor=white) ![Google ADK](https://img.shields.io/badge/Google_ADK-4285F4?style=for-the-badge&logo=google&logoColor=white) ![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-black?style=for-the-badge) ![MCP](https://img.shields.io/badge/MCP-Protocol-purple?style=for-the-badge)

*Developed as part of the **5-Day AI Agents Intensive Course with Google**.*

Este proyecto implementa un agente de Inteligencia Artificial diseñado para consultar una base de datos clínica SQL Server y responder preguntas estadísticas complejas en lenguaje natural. Está construido de manera profesional y modular, aislando los datos sensibles del hospital (PHI) mediante el uso de un modelo local de **Ollama** y exponiendo el acceso a la base de datos a través de un servidor de **Model Context Protocol (MCP)** reutilizable y seguro.

## Arquitectura del Proyecto

```text
agentes-adk/
├── .agents/
│   └── skills/
│       ├── clinical-statistics/ # Skill (Intent Routing y extracción de parámetros)
│
├── src/
│   ├── __init__.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── connection.py      # Conexión a la base de datos (pyodbc)
│   │   └── operations.py      # Consultas SQL seguras y Pandas DataFrames
│   ├── mcp/
│   │   ├── __init__.py
│   │   └── server.py          # Servidor FastMCP que expone las herramientas de BD
│   └── agent/
│       ├── __init__.py
│       └── agent.py           # Configuración del Agente ADK con Ollama y herramientas MCP
├── .env                       # Variables de entorno (SQL Server, Ollama y API keys)
├── requirements.txt           # Dependencias de Python
├── main.py                    # Consola de chat interactiva con el agente
└── run_mcp.py                 # Lanzador del servidor MCP independiente (Stdio o HTTP/SSE)
```

---

## Requisitos Previos

1.  **Python 3.10+**
2.  **Driver ODBC de SQL Server:** Asegúrate de tener instalado "ODBC Driver 17 for SQL Server".
3.  **Servidor de Ollama:** Debe estar corriendo en la red local (ej: `xxxx`) con el modelo `xxx` descargado.

---

## Configuración de Inicio

### 1. Preparar el Entorno Virtual

#### En Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

#### Instalar Dependencias:
```bash
pip install -r requirements.txt
```

### 2. Configurar Variables de Entorno (`.env`)

Edita el archivo `.env` en la raíz con tus credenciales reales:

```env
# Conexión SQL Server (Se recomienda un usuario de SOLO LECTURA)
DB_HOST=10.xx.0.X
DB_NAME=xx
DB_USER=usuario_solo_lectura
DB_PASSWORD=contraseña_segura
DB_PORT=xxx

# Ollama Local (Resguardo de datos del hospital)
OLLAMA_API_BASE=http://xxx.xxx.xxx.xxx:xxx
LLM_MODEL_QA=xxxxx
```

---

## Ejecución del Proyecto

### Opción A: Interfaz de Consola Interactiva (Agente completo)
Este script inicia el agente ADK, el cual levanta automáticamente el servidor MCP de base de datos de forma interna, conectándose a Ollama para procesar tus preguntas:
```bash
python main.py
```

### Opción B: Interfaz Web Oficial de ADK
Puedes interactuar con tu agente utilizando la interfaz web integrada del ADK, ideal para depurar visualmente los pasos cognitivos de Ollama y las consultas SQL ejecutadas:
```bash
adk web src/agent

```

### Opción C: Ejecutar el Servidor MCP de Forma Independiente (SSE)
Si quieres que otros agentes o sistemas externos (como Claude Desktop o cursores de desarrollo) consuman tus consultas SQL, puedes levantar el servidor de base de datos como un servicio web HTTP/SSE independiente:
```bash
fastmcp run src/mcp/server.py --transport http --port 8000
```

---

## Seguridad y Control de Datos
1.  **Modelo Local:** Los datos clínicos y las consultas de la historia clínica se procesan 100% en tu servidor de Ollama (`xxx`), por lo que no viajan a internet ni a APIs públicas de terceros.
2.  **Validación de Consultas:** La herramienta `query_clinical_statistics` implementa una verificación estricta en `src/db/operations.py` para asegurar que las consultas del agente comiencen únicamente con `SELECT` o `WITH` y rechaza palabras destructivas como `DROP`, `DELETE`, `UPDATE`, `INSERT`, etc.
