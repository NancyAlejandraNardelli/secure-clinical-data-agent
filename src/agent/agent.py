import os
import sys

# Suprimir el logging de LiteLLM ANTES de cualquier import que lo cargue.
# El LoggingWorker de LiteLLM intenta enviar métricas a servidores remotos;
# en entornos sin internet esto genera errores de timeout constantes.
os.environ["LITELLM_LOG"] = "ERROR"
os.environ["LITELLM_TELEMETRY"] = "False"

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from google.genai import types

# Cargar variables de entorno
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(dotenv_path=os.path.join(base_dir, '.env'))

# Configurar OLLAMA_API_BASE en el entorno para LiteLLM
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://10.10.0.48:11434")
os.environ["OLLAMA_API_BASE"] = OLLAMA_API_BASE

# Habilitar Fallback a Gemini si está configurado
USE_GEMINI = os.getenv("USE_GEMINI", "false").lower() == "true"

if USE_GEMINI and os.getenv("GEMINI_API_KEY"):
    from google.adk.models.google_llm import Gemini
    active_llm = Gemini(model_name="gemini-2.5-flash")
else:
    # Configurar el modelo local usando LiteLlm
    model_name = os.getenv("LLM_MODEL_QA", "ministral-3:3b-instruct-2512-q8_0")
    active_llm = LiteLlm(
        model=f"ollama_chat/{model_name}",
        api_base=OLLAMA_API_BASE
    )

# Desactivar callbacks de logging de LiteLLM que intentan conectar a
# servidores externos y generan errores de timeout en entornos sin salida a internet.
import litellm
litellm.success_callback = []
litellm.failure_callback = []
litellm._async_success_callback = []
litellm._async_failure_callback = []

# Ruta al script del servidor MCP
server_script = os.path.join(base_dir, "src", "mcp", "server.py")

# Parámetros de conexión Stdio para el servidor MCP
# Detectar el ejecutable de python en el entorno virtual del proyecto (.venv)
venv_python = os.path.join(base_dir, ".venv", "Scripts", "python.exe")
python_executable = venv_python if os.path.exists(venv_python) else sys.executable

server_params = StdioServerParameters(
    command=python_executable,
    args=[server_script],
    env=os.environ.copy()
)

from datetime import datetime
fecha_actual_str = datetime.now().strftime("%Y-%m-%d")

system_instruction = f"""Eres un Asistente Senior de Estadísticas Clínicas y Datos Médicos.
Tu único objetivo es responder a las consultas estadísticas del usuario sobre la vista 'v_historiaClinica'.

La fecha actual del sistema es: {fecha_actual_str}. Utiliza esta fecha de referencia cuando el usuario te consulte términos relativos como "este mes", "el año pasado", o "hace 30 días".

Para ello, debes utilizar SIEMPRE la herramienta 'consultar_estadisticas_hc' para obtener los reportes.

Tienes a tu disposición el SKILL 'clinical-statistics' para estructurar la llamada. Tu único trabajo es:
1. Extraer las dimensiones de agrupación solicitadas por el usuario y pasarlas en el parámetro 'agrupar_por' como una lista/array de strings (ej: ['zona', 'edad'], ['servicio', 'especialidad'], o ['diagnostico', 'zona']).
   Mapea los términos del usuario a las siguientes dimensiones permitidas:
   - "procedencia", "localidad", "barrio", "zona" -> "zona"
   - "edad", "grupo etario", "rango etario" -> "edad"
   - "sexo", "genero" -> "sexo"
   - "servicio", "unidad" -> "servicio"
   - "especialidad" -> "especialidad"
   - "diagnostico", "patologia", "estructura" -> "diagnostico"
   - "obra social", "cobertura", "prepaga" -> "obra_social"
   - "año", "year", "fecha" -> "año"
   - "mes", "month" -> "mes"
2. Si el usuario menciona una o más condiciones, diagnósticos o medicamentos que DEBEN estar presentes, pásalos en el parámetro 'filtros_si' (separados por coma si son varios, ej: 'Hipertensión, Amlodipina').
3. Si el usuario menciona condiciones o medicamentos que NO deben estar presentes, pásalos en el parámetro 'filtros_no' (separados por coma si son varios, ej: 'Enalapril').
4. Si se especifican fechas de atención o visitas, extrae e inyecta 'fecha_inicio' o 'fecha_fin' en formato 'YYYY-MM-DD'.
5. Si preguntan por diagnósticos activos, establece 'solo_activos=True'.
6. Si especifican secciones de la historia clínica (como motivo de consulta, evolución, etc.), pásalo en 'tipo_registro'.
7. IMPORTANTE - Lógica AND vs OR en filtros clínicos (parámetro 'modo_filtro'):
   - Usa modo_filtro='AND' (default) cuando el usuario quiere pacientes que tengan TODOS los términos simultáneamente.
     Señales lingüísticas: "X e Y", "X con Y", "X y Y", "que tengan ambos", "diagnosticados con X y también con Y".
   - Usa modo_filtro='OR' cuando el usuario quiere pacientes que tengan CUALQUIERA de los términos.
     Señales lingüísticas: "X o Y", "X u Y", "cualquiera de", "alguno de", "ya sea X o Y".
   Ejemplo: "pacientes con Neumonía o Bronquiolitis" → filtros_si='Neumonía, Bronquiolitis', modo_filtro='OR'
   Ejemplo: "pacientes con Hipertensión y Diabetes" → filtros_si='Hipertensión, Diabetes', modo_filtro='AND'
 8. MÉTRICAS ESTADÍSTICAS (parámetro 'metricas'):
   - Usa metricas='conteo' (default) para contar pacientes o registros (comportamiento normal).
   - Usa metricas='estadisticas_edad' cuando el usuario pregunte por:
     Promedio de edad, mediana de edad, distribución etaria numérica, rango de edades,
     percentiles de edad, desvío estándar de edad, o cualquier métrica numérica sobre la edad.
     Señales lingüísticas: "promedio de edad", "edad media", "mediana de edad", "rango etario numérico",
     "¿qué tan viejos son?", "perfil etario estadístico", "estadísticas de edad".
     Ejemplo: "¿Cuál es el promedio de edad de los pacientes con Asma?" → filtros_si='Asma', metricas='estadisticas_edad'
   - Usa metricas='estadisticas_visitas' cuando el usuario pregunte por:
     Promedio de visitas, mediana de visitas/consultas, desvío de consultas, total de visitas promedio por paciente.
     Señales lingüísticas: "promedio de visitas", "mediana de consultas", "promedio de consultas por paciente", "desvío estándar de visitas".
     Ejemplo: "¿Cuál es el promedio de visitas por paciente para los hipertensos?" → filtros_si='Hipertensión', metricas='estadisticas_visitas'
   - Usa metricas='estadisticas_antiguedad' cuando el usuario pregunte por:
     Antigüedad promedio del diagnóstico/enfermedad en días, días transcurridos desde el diagnóstico, tiempo promedio con la enfermedad.
     Señales lingüísticas: "antigüedad promedio del diagnóstico", "antigüedad de la enfermedad", "tiempo promedio con diabetes", "días transcurridos desde el diagnóstico".
     Ejemplo: "¿Cuál es la antigüedad promedio del diagnóstico de asma en días?" → filtros_si='Asma', metricas='estadisticas_antiguedad'

REGLAS GLOBALES INQUEBRANTABLES:
- NUNCA hagas preguntas aclaratorias ni pidas confirmación al usuario. Si el usuario te hace una pregunta, llama a la herramienta 'consultar_estadisticas_hc' inmediatamente.
- NUNCA uses tu conocimiento pre-entrenado general para responder preguntas médicas ni inventar estadísticas. Tu única fuente de verdad son los datos devueltos por la herramienta.
- PROHIBIDO escribir consultas SQL manuales.
- PROHIBIDO analizar los resultados. Tu ejecución termina al llamar a la herramienta.
- IMPRIME EL RESULTADO EXACTO DE LA HERRAMIENTA. No agregues resúmenes, viñetas ni análisis clínicos. Tu respuesta debe consistir ÚNICAMENTE en lo que te devuelve el sistema.
"""

def extract_clean_table(events) -> str | None:
    for event in reversed(events):
        func_resps = event.get_function_responses()
        if func_resps:
            for fr in func_resps:
                if fr.name in ("consultar_estadisticas_hc", "get_demographic_stats", "query_clinical_statistics"):
                    resp_payload = fr.response
                    table_data = None
                    if isinstance(resp_payload, dict):
                        content_list = resp_payload.get("content", [])
                        if content_list and isinstance(content_list, list):
                            table_data = content_list[0].get("text", "")
                    elif isinstance(resp_payload, str):
                        table_data = resp_payload
                    
                    if table_data:
                        if "\n\n---\n" in table_data:
                            table_data = table_data.split("\n\n---\n")[0]
                        elif "\n---\n" in table_data:
                            table_data = table_data.split("\n---\n")[0]
                            
                        # Ocultar la consulta SQL del front del usuario (el programador la verá en los Traces)
                        if "### Consulta SQL Ejecutada:" in table_data:
                            table_data = table_data.split("### Consulta SQL Ejecutada:")[0]
                            
                        return table_data.strip()
    return None

def clean_llm_text(text: str) -> str:
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") or (stripped.startswith("---") and "|" in stripped):
            break
        if "Nota:" in line or "omito" in line or "omitido" in line or "exceder" in line:
            break
        cleaned_lines.append(line)
    result = "\n".join(cleaned_lines).strip()
    if not result:
        result = "Aquí tienes los resultados solicitados:"
    return result

async def my_after_model_callback(callback_context, llm_response):
    if os.environ.get("IS_CLI_MODE") == "TRUE":
        return llm_response

    table = extract_clean_table(callback_context.session.events)
    if not table:
        return llm_response

    if llm_response.content and llm_response.content.parts:
        text_part = None
        for part in llm_response.content.parts:
            if hasattr(part, 'text') and part.text is not None:
                text_part = part
                break
        
        if text_part:
            cleaned_text = clean_llm_text(text_part.text)
            text_part.text = f"{cleaned_text}\n\n{table}"
        else:
            llm_response.content.parts.append(types.Part(text=f"\n\n{table}"))
    else:
        p = types.Part(text=f"\n\n{table}")
        llm_response.content = types.Content(role='model', parts=[p])

    return llm_response

# Definir el agente raíz del ADK
# El McpToolset se instancia aquí con sus parámetros de conexión.
# ADK lo inicializará correctamente dentro del runner async.
root_agent = LlmAgent(
    name="agente_estadisticas_clinicas",
    model=active_llm,
    instruction=system_instruction,
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=server_params,
                timeout=120.0
            )
        )
    ],
    after_model_callback=my_after_model_callback
)
