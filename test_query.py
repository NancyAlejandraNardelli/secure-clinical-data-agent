import os
# Indicar que estamos en modo CLI para habilitar el bypass puro
os.environ["IS_CLI_MODE"] = "TRUE"

import asyncio
import logging
from contextlib import aclosing
from google.genai import types
from google.adk.runners import InMemoryRunner
from src.agent.agent import root_agent
from main import extraer_respuesta_final, imprimir_structured_content, es_respuesta_de_herramienta

# Silenciar logs innecesarios
logging.basicConfig(level=logging.ERROR)
logging.getLogger("google.adk").setLevel(logging.ERROR)
logging.getLogger("litellm").setLevel(logging.ERROR)

async def test():
    runner = InMemoryRunner(agent=root_agent)
    prompt = "Mostrame un reporte de cuántos pacientes con Diabetes fueron atendidos, agrupados por Servicio y Especialidad."
    print("\nProcesando consulta...\n")
    
    # Limpiar cualquier archivo temporal residual antes de iniciar la consulta
    if os.path.exists(".ui_payload.md"):
        os.remove(".ui_payload.md")
        
    session = await runner.session_service.get_session(
        app_name=runner.app_name,
        user_id="test_user",
        session_id="test_session",
    )
    if not session:
        session = await runner.session_service.create_session(
            app_name=runner.app_name,
            user_id="test_user",
            session_id="test_session"
        )
        
    events = []
    cortocircuito = False
    
    async with aclosing(
        runner.run_async(
            user_id="test_user",
            session_id=session.id,
            new_message=types.UserContent(parts=[types.Part(text=prompt)]),
        )
    ) as agen:
        async for event in agen:
            events.append(event)
            if es_respuesta_de_herramienta(event) and os.path.exists(".ui_payload.md"):
                imprimir_structured_content(events)
                print("\n[Sistema]: Reporte generado con éxito en UI. Fin de la consulta.")
                cortocircuito = True
                break
                
    if not cortocircuito:
        respuesta = extraer_respuesta_final(events)
        print(f"Agente:\n{respuesta}")

if __name__ == "__main__":
    asyncio.run(test())
