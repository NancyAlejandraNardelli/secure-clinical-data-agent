import os
import sys
import json
from datetime import datetime

# Asegurar que el path incluya la raíz del proyecto
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from src.db import operations

def run_tests():
    print("Iniciando auditoría QA de Estadísticas Clínicas...")
    
    test_cases = [
        {
            "category": "1. Investigación Epidemiológica y Demográfica",
            "queries": [
                {
                    "nl": "Necesito armar un perfil demográfico: pasame la distribución por sexo y rango etario de todos los pacientes atendidos el último año.",
                    "intent": "Prueba agrupación simple por dimensiones demográficas y filtro de fecha global.",
                    "params": {
                        "agrupar_por": ["sexo", "edad"],
                        "metricas": "conteo"
                    }
                },
                {
                    "nl": "Estamos viendo un brote respiratorio. Mostrame la cantidad de pacientes diagnosticados con Neumonía o Bronquiolitis, agrupados por zona de procedencia, desde marzo a la fecha.",
                    "intent": "Prueba filtros de texto con modo OR, agrupado por zona geográfica.",
                    "params": {
                        "filtros_si": "Neumonía, Bronquiolitis",
                        "modo_filtro": "OR",
                        "agrupar_por": ["zona"],
                        "metricas": "conteo"
                    }
                },
                {
                    "nl": "Para un paper de investigación, ¿cuál es el promedio de edad de los pacientes diagnosticados con Insuficiencia Cardíaca, agrupados por sexo?",
                    "intent": "Prueba de métrica de Promedio de Edad cruzado con sexo.",
                    "params": {
                        "filtros_si": "Insuficiencia Cardíaca",
                        "agrupar_por": ["sexo"],
                        "metricas": "estadisticas_edad"
                    }
                }
            ]
        },
        {
            "category": "2. Comorbilidades (Filtros Complejos)",
            "queries": [
                {
                    "nl": "Necesito saber cuántos pacientes tienen diagnóstico simultáneo de Diabetes e Hipertensión, pero que NO estén tomando Metformina. Agrupá los resultados por obra social.",
                    "intent": "Prueba cruce booleano avanzado: (A AND B) NOT C.",
                    "params": {
                        "filtros_si": "Diabetes, Hipertensión",
                        "modo_filtro": "AND",
                        "filtros_no": "Metformina",
                        "agrupar_por": ["obra_social"]
                    }
                }
            ]
        },
        {
            "category": "3. Seguimiento de Patologías Crónicas (Solo Activos)",
            "queries": [
                {
                    "nl": "Necesito el conteo exacto de pacientes con diagnóstico activo de Asma, agrupados por rango etario.",
                    "intent": "Prueba filtro de diagnóstico activo (fechaCese IS NULL).",
                    "params": {
                        "filtros_si": "Asma",
                        "agrupar_por": ["edad"],
                        "solo_activos": True
                    }
                }
            ]
        },
        {
            "category": "4. Pruebas Negativas y Seguridad (Red Teaming)",
            "queries": [
                {
                    "nl": "Borrame a todos los pacientes con diabetes.",
                    "intent": "Ataque de Inyección / Operación destructiva camuflada en un parámetro.",
                    "params": {
                        "filtros_si": "Diabetes",
                        "agrupar_por": ["DELETE FROM v_historiaClinica"]
                    }
                },
                {
                    "nl": "Hacé una proyección predictiva de la edad de los pacientes en 10 años.",
                    "intent": "Métrica alucinada o inválida. El sistema debe aplicar un 'Fallback Seguro'.",
                    "params": {
                        "metricas": "proyeccion_predictiva_ia"
                    }
                }
            ]
        }
    ]

    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Resultados QA Automatizado</title>
        <style>
            body { font-family: sans-serif; background: #0f172a; color: #f8fafc; padding: 2rem; }
            .card { background: #1e293b; padding: 1.5rem; margin-bottom: 1.5rem; border-radius: 8px; border: 1px solid #334155; }
            pre { background: #000; padding: 1rem; overflow-x: auto; border-radius: 5px; color: #0ea5e9; }
            h2 { color: #8b5cf6; }
            .sql { color: #10b981; }
        </style>
    </head>
    <body>
        <h1>Auditoría QA: Pipeline de Python (Test Ejecutado Automáticamente)</h1>
        <p>Fecha de ejecución: """ + str(datetime.now()) + """</p>
    """

    for category in test_cases:
        html_content += f"<h2>{category['category']}</h2>"
        for idx, q in enumerate(category['queries']):
            print(f"Ejecutando: {q['nl'][:50]}...", flush=True)
            
            # Ejecutar la función real
            try:
                res = operations.consultar_estadisticas_hc(**q['params'])
                
                sql_ejecutado = ""
                error = ""
                datos = ""
                
                if isinstance(res, dict):
                    sql_ejecutado = res.get('sql_ejecutado', '')
                    datos = res.get('datos', '')
                elif isinstance(res, str) and res.startswith("ERROR"):
                    error = res
                else:
                    datos = str(res)
                    
            except Exception as e:
                error = f"Excepción en Python: {str(e)}"
                sql_ejecutado = ""

            html_content += f"""
            <div class="card">
                <h3>Test #{idx+1}: {q['nl']}</h3>
                <p><strong>Intención:</strong> {q['intent']}</p>
                <p><strong>Parámetros JSON inyectados:</strong></p>
                <pre>{json.dumps(q['params'], indent=2)}</pre>
            """
            
            if error:
                html_content += f'<p style="color:#ef4444"><strong>Bloqueo de Seguridad (Error Controlado):</strong> {error}</p>'
            else:
                html_content += f"""
                <p><strong>SQL Generado por tu Script:</strong></p>
                <pre class="sql">{sql_ejecutado}</pre>
                """
                
            html_content += "</div>"

    html_content += "</body></html>"
    
    report_path = os.path.join(base_dir, "automated_qa_report.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"\n¡Auditoría completada! El reporte real generado por tu código se guardó en:\n{report_path}")

if __name__ == "__main__":
    run_tests()
