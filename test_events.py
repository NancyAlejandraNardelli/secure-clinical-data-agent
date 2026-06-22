import asyncio
from google.adk.runners import InMemoryRunner
from src.agent.agent import root_agent

async def test():
    runner = InMemoryRunner(agent=root_agent)
    prompt = "Mostrame un reporte de cuántos pacientes con Diabetes fueron atendidos, agrupados por Servicio y Especialidad."
    events = await runner.run_debug(prompt, verbose=False)
    for event in events:
        print(f"EVENT: {type(event)}")
        if hasattr(event, "content") and event.content:
            for part in event.content.parts:
                print(f"  PART:")
                if getattr(part, "function_call", None):
                    print(f"    function_call: {part.function_call}")
                if getattr(part, "function_response", None):
                    print(f"    function_response: {part.function_response.name} -> {type(part.function_response.response)}")
                    # print snippet
                    resp_str = str(part.function_response.response)
                    print(f"    {resp_str[:100]}...")
                if getattr(part, "text", None) and not getattr(part, "function_call", None) and not getattr(part, "function_response", None):
                    print(f"    text: {part.text[:100]}...")

if __name__ == "__main__":
    asyncio.run(test())
