import asyncio
import traceback
import warnings
import logging
import os
from contextlib import aclosing
from google.genai import types

# Configurar logging para silenciar advertencias de cancelación de tareas esperadas
logging.basicConfig(level=logging.ERROR)
logging.getLogger("google.adk").setLevel(logging.ERROR)
logging.getLogger("litellm").setLevel(logging.ERROR)

# Indicar que estamos en modo CLI para habilitar el bypass puro
os.environ["IS_CLI_MODE"] = "TRUE"

# Ruta absoluta al archivo temporal del reporte
UI_PAYLOAD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".ui_payload.md")

# Suprimir advertencias de features experimentales de ADK (son informativas, no errores)
warnings.filterwarnings("ignore", category=UserWarning, module="google.adk")
from google.adk.runners import InMemoryRunner
from src.agent.agent import root_agent


def extraer_respuesta_final(events: list) -> str:
    """Extrae el texto de la última respuesta del modelo en la lista de eventos."""
    respuesta = ""
    for event in events:
        if (
            hasattr(event, "content")
            and event.content
            and hasattr(event.content, "parts")
            and event.content.parts
        ):
            for part in event.content.parts:
                es_texto_puro = (
                    hasattr(part, "text")
                    and part.text
                    and not getattr(part, "function_call", None)
                    and not getattr(part, "function_response", None)
                )
                if es_texto_puro:
                    respuesta = part.text  # Nos quedamos con el último texto
    return respuesta.strip() if respuesta else "(Sin respuesta)"


def es_respuesta_de_herramienta(event) -> bool:
    """Verifica si el evento es una respuesta de ejecución de herramienta."""
    if hasattr(event, "content") and event.content and hasattr(event.content, "parts"):
        for part in event.content.parts:
            if getattr(part, "function_response", None):
                return True
    return False


def imprimir_structured_content(events: list):
    """Extrae e imprime las respuestas de las herramientas (Structured Content) directamente a la UI."""
    if os.path.exists(UI_PAYLOAD_PATH):
        with open(UI_PAYLOAD_PATH, "r", encoding="utf-8") as f:
            tabla = f.read().strip()
            if tabla:
                if "### Consulta SQL Ejecutada:" in tabla:
                    parts = tabla.split("### Consulta SQL Ejecutada:")
                    tabla_user = parts[0].strip()
                    sql_dev = parts[1].strip()
                    print("\n=== DATOS DEL REPORTE (Structured Content) ===")
                    print(tabla_user)
                    print("==============================================\n")
                    print("\n[DEBUG PROGRAMADOR] Consulta SQL Ejecutada:")
                    print(sql_dev)
                    print("----------------------------------------------\n")
                else:
                    print("\n=== DATOS DEL REPORTE (Structured Content) ===")
                    print(tabla)
                    print("==============================================\n")
        os.remove(UI_PAYLOAD_PATH)


async def main():
    print("=====================================================================")
    print("INICIANDO AGENTE DE ESTADÍSTICAS CLÍNICAS (LOCAL OLLAMA + SQL SERVER)")
    print("=====================================================================")
    print("Inicializando el orquestador InMemoryRunner y levantando MCP Server...")

    runner = InMemoryRunner(agent=root_agent)

    print("\n¡Listo! Escribe tu pregunta estadística sobre los datos médicos.")
    print("Ejemplos:")
    print(" - ¿Cuál es el promedio de edad de los pacientes por género?")
    print(" - ¿Cuáles son las columnas y tipos de datos de v_historiaClinica?")
    print(" - Dame las especialidades para el servicio ID 14.")
    print("Escribe 'salir' para terminar.\n")

    # Iniciar o recuperar sesión de ejecución única persistente para la interacción de la consola
    session = await runner.session_service.get_session(
        app_name=runner.app_name,
        user_id="console_user",
        session_id="console_session",
    )
    if not session:
        session = await runner.session_service.create_session(
            app_name=runner.app_name,
            user_id="console_user",
            session_id="console_session"
        )

    while True:
        try:
            prompt = input("Tú: ")
            if prompt.strip().lower() == "salir":
                break
            if not prompt.strip():
                continue

            # Limpiar cualquier archivo temporal residual antes de iniciar la consulta
            if os.path.exists(UI_PAYLOAD_PATH):
                os.remove(UI_PAYLOAD_PATH)

            print("\nProcesando consulta con Ollama y herramientas SQL Server (MCP)...\n")

            events = []
            cortocircuito = False

            # Ejecutar el runner de forma asíncrona iterando sus eventos paso a paso
            async with aclosing(
                runner.run_async(
                    user_id="console_user",
                    session_id=session.id,
                    new_message=types.UserContent(parts=[types.Part(text=prompt)]),
                )
            ) as agen:
                async for event in agen:
                    events.append(event)
                    # Cortocircuitar SOLO cuando el evento es una respuesta de herramienta Y existe el payload de reporte
                    if es_respuesta_de_herramienta(event) and os.path.exists(UI_PAYLOAD_PATH):
                        imprimir_structured_content(events)
                        print("\n[Sistema]: Reporte generado con éxito en UI. Fin de la consulta.")
                        cortocircuito = True
                        break  # Termina el loop asíncrono cancelando el agente y evitando que el LLM hable

            if not cortocircuito:
                # Si no hubo cortocircuito (ej: preguntas informativas generales), procesar el cierre del LLM
                respuesta = extraer_respuesta_final(events)
                print(f"Agente:\n{respuesta}")

            print("\n" + "-" * 70)

        except KeyboardInterrupt:
            print("\n[Saliendo del agente...]")
            break
        except Exception as e:
            print(f"\nOcurrió un error al ejecutar la consulta: {e}")
            traceback.print_exc()
            print()


if __name__ == "__main__":
    asyncio.run(main())
