import sys
import os
import json
from fastmcp import FastMCP

# Agregar el directorio raíz al PATH de Python
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from src.db import operations

# Inicializar el servidor MCP
mcp = FastMCP("SQL Server Clinical Stats Server")

@mcp.tool()
def consultar_estadisticas_hc(
    agrupar_por: list[str] = None,
    filtros_si: str = None,
    filtros_no: str = None,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    solo_activos: bool = False,
    tipo_registro: str = None,
    tipo_conteo: str = "pacientes"
) -> str:
    """Consulta estadísticas de pacientes en la vista v_historiaClinica.
    
    Parámetros:
    - agrupar_por: Lista/array de dimensiones de agrupación. Dimensiones válidas:
      - 'edad' (grupos etarios).
      - 'sexo' (distribución por sexo).
      - 'zona' (distribución por procedencia).
      - 'servicio' (distribución por servicio).
      - 'especialidad' (distribución por especialidad).
      - 'diagnostico' (distribución por diagnóstico/motivo en estructura).
      - 'obra_social' (distribución por obra social).
      - 'año' (año de visita).
      - 'mes' (mes de visita).
      Si la lista está vacía o es None, se devuelve el conteo total de pacientes únicos.
    - filtros_si: Término o lista de términos separados por coma que DEBEN estar presentes (ej: 'Hipertensión, Amlodipina').
    - filtros_no: Término o lista de términos separados por coma que NO deben estar presentes (ej: 'Enalapril').
    - fecha_inicio: Fecha de inicio en formato 'YYYY-MM-DD' para filtrar visitas.
    - fecha_fin: Fecha de fin en formato 'YYYY-MM-DD' para filtrar visitas.
    - solo_activos: Filtrar solo diagnósticos que siguen activos (fechaCese nulo o futuro).
    - tipo_registro: Filtrar por tipo de registro o estructura (ej: 'Motivo de consulta', 'EVOLUCIÓN').
    - tipo_conteo: Determina si se cuentan pacientes únicos ("pacientes") o total de visitas/registros ("registros").
    """
    res = operations.consultar_estadisticas_hc(
        agrupar_por=agrupar_por,
        filtros_si=filtros_si,
        filtros_no=filtros_no,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        solo_activos=solo_activos,
        tipo_registro=tipo_registro,
        tipo_conteo=tipo_conteo
    )
    
    if isinstance(res, str) and res.startswith("ERROR"):
        return res
        
    tabla = res['datos'] if isinstance(res, dict) else res
    sql = res['sql_ejecutado'] if isinstance(res, dict) else ""
    
    payload = f"{tabla}"
    if sql:
        payload += f"\n\n### Consulta SQL Ejecutada:\n```sql\n{sql}\n```"
        
    if os.environ.get("IS_CLI_MODE") == "TRUE":
        # Bypass puro para CLI
        ui_path = os.path.join(base_dir, ".ui_payload.md")
        with open(ui_path, "w", encoding="utf-8") as f:
            f.write(payload)
        return "Datos procesados y mostrados en pantalla. NO intentes resumir ni analizar nada. Solo responde: 'Aquí tienes los resultados solicitados.'"
    else:
        # Modo Web: retornamos la tabla completa directamente al LLM con una instrucción de evitar duplicación
        instrucciones_agente = (
            "\n\n---\n"
            "[SISTEMA - INSTRUCCIÓN CRÍTICA]: Para evitar límites de tokens y respuestas truncadas, "
            "NO intentes copiar, reproducir ni resumir la tabla anterior ni el SQL en tu mensaje de respuesta. El sistema "
            "se encargará de inyectar y mostrar la tabla de forma automática por ti. Responde ÚNICAMENTE "
            "con un saludo/introducción breve (por ejemplo: 'Aquí tienes los resultados solicitados:') "
            "y NADA MÁS. No agregues tablas ni viñetas adicionales."
        )
        return payload + instrucciones_agente

if __name__ == "__main__":
    # fastmcp requiere indicar el transporte
    mcp.run(transport="stdio")
