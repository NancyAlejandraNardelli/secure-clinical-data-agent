import sys
from src.mcp.server import mcp

if __name__ == "__main__":
    print("Iniciando el servidor de Estadísticas SQL Server (MCP)...")
    # Por defecto corre en modo stdio, pero puede aceptar argumentos del CLI de fastmcp
    # para correr como SSE (--transport http --port 8000).
    mcp.run()
