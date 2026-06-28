"""
🔄 Dev Server con Hot-Reload para ADK Web
==========================================
Vigila cambios en archivos .py del proyecto y reinicia automáticamente
el servidor `adk web` sin necesidad de hacer Ctrl+C manualmente.

Uso:
    python dev.py              # Inicia adk web con hot-reload
    python dev.py --port 8080  # Cambia el puerto (default: 8000)
    python dev.py --cli        # Usa main.py en vez de adk web
"""

import sys
import os
import time
import signal
import subprocess
import argparse
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Colores ANSI para la terminal
class Colors:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

PROJECT_DIR = Path(__file__).parent.resolve()

# Directorios/archivos a ignorar
IGNORE_DIRS = {".venv", "__pycache__", ".git", "node_modules", ".agents", "data"}
IGNORE_FILES = {"dev.py"}  # No reiniciar por cambios en este mismo archivo


class ReloadHandler(FileSystemEventHandler):
    """Detecta cambios en archivos .py y dispara un reinicio."""

    def __init__(self, restart_callback):
        super().__init__()
        self.restart_callback = restart_callback
        self._last_trigger = 0
        self._debounce_seconds = 1.5  # Evitar múltiples reinicios por saves rápidos

    def _should_ignore(self, path: str) -> bool:
        p = Path(path)
        # Ignorar directorios excluidos
        for part in p.parts:
            if part in IGNORE_DIRS:
                return True
        # Ignorar archivos excluidos
        if p.name in IGNORE_FILES:
            return True
        return False

    def on_modified(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith(".py"):
            return
        if self._should_ignore(event.src_path):
            return

        now = time.time()
        if now - self._last_trigger < self._debounce_seconds:
            return
        self._last_trigger = now

        rel_path = os.path.relpath(event.src_path, PROJECT_DIR)
        print(f"\n{Colors.YELLOW}📝 Cambio detectado: {rel_path}{Colors.RESET}")
        self.restart_callback()


class DevServer:
    """Gestiona el proceso del servidor ADK con auto-reinicio."""

    def __init__(self, mode="web", port=8000):
        self.mode = mode
        self.port = port
        self.process = None
        self._restart_count = 0

    def _build_command(self) -> list[str]:
        if self.mode == "cli":
            return [sys.executable, str(PROJECT_DIR / "main.py")]
        else:
            # adk es un CLI entry point, no un módulo ejecutable con -m
            adk_exe = PROJECT_DIR / ".venv" / "Scripts" / "adk.exe"
            adk_cmd = str(adk_exe) if adk_exe.exists() else "adk"
            return [
                adk_cmd, "web",
                str(PROJECT_DIR / "src" / "agent"),
                "--port", str(self.port),
            ]

    def start(self):
        """Inicia el proceso del servidor."""
        self._restart_count += 1
        cmd = self._build_command()

        if self._restart_count == 1:
            print(f"{Colors.CYAN}{Colors.BOLD}")
            print("=" * 60)
            print("  🚀 Dev Server con Hot-Reload")
            print("=" * 60)
            print(f"{Colors.RESET}")
            print(f"  {Colors.GREEN}Modo:{Colors.RESET}    {self.mode}")
            if self.mode == "web":
                print(f"  {Colors.GREEN}Puerto:{Colors.RESET}  {self.port}")
                print(f"  {Colors.GREEN}URL:{Colors.RESET}    http://localhost:{self.port}")
            print(f"  {Colors.GREEN}Watch:{Colors.RESET}   src/**/*.py")
            print(f"  {Colors.GREEN}Comando:{Colors.RESET} {' '.join(cmd)}")
            print(f"\n  {Colors.MAGENTA}Editá cualquier .py y el servidor se reinicia solo ✨{Colors.RESET}")
            print(f"  {Colors.MAGENTA}Presioná Ctrl+C para salir completamente.{Colors.RESET}\n")
        else:
            print(f"\n{Colors.CYAN}🔄 Reiniciando servidor (reinicio #{self._restart_count - 1})...{Colors.RESET}\n")

        # Pasar el entorno actual (incluye .env cargado por el agente)
        env = os.environ.copy()
        
        self.process = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_DIR),
            env=env,
            # No capturamos stdout/stderr para que se vean en la terminal
        )
        
        print(f"{Colors.GREEN}✅ Servidor iniciado (PID: {self.process.pid}){Colors.RESET}\n")

    def stop(self):
        """Detiene el proceso del servidor de forma limpia."""
        if self.process and self.process.poll() is None:
            print(f"{Colors.YELLOW}⏹️  Deteniendo servidor (PID: {self.process.pid})...{Colors.RESET}")
            try:
                # En Windows, usamos taskkill para matar el árbol de procesos
                # (el servidor MCP crea subprocesos)
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                        capture_output=True,
                    )
                else:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                    self.process.wait(timeout=5)
            except Exception:
                self.process.kill()
            self.process = None

    def restart(self):
        """Reinicia el servidor (stop + start)."""
        self.stop()
        time.sleep(0.5)  # Breve pausa para liberar el puerto
        self.start()


def main():
    parser = argparse.ArgumentParser(description="Dev server con hot-reload para ADK")
    parser.add_argument("--port", type=int, default=8000, help="Puerto para adk web (default: 8000)")
    parser.add_argument("--cli", action="store_true", help="Usar main.py en vez de adk web")
    args = parser.parse_args()

    mode = "cli" if args.cli else "web"
    server = DevServer(mode=mode, port=args.port)

    # Configurar el watcher de archivos
    handler = ReloadHandler(restart_callback=server.restart)
    observer = Observer()
    observer.schedule(handler, str(PROJECT_DIR / "src"), recursive=True)
    observer.start()

    # Iniciar el servidor por primera vez
    server.start()

    try:
        while True:
            time.sleep(1)
            # Si el proceso murió por un crash, informar pero no reiniciar automáticamente
            if server.process and server.process.poll() is not None:
                exit_code = server.process.returncode
                if exit_code != 0:
                    print(f"\n{Colors.RED}💥 El servidor crasheó (exit code: {exit_code}).{Colors.RESET}")
                    print(f"{Colors.YELLOW}   Esperando cambios en archivos para reiniciar...{Colors.RESET}\n")
                    server.process = None
    except KeyboardInterrupt:
        print(f"\n{Colors.CYAN}👋 Cerrando dev server...{Colors.RESET}")
    finally:
        observer.stop()
        observer.join()
        server.stop()
        print(f"{Colors.GREEN}✅ Dev server cerrado limpiamente.{Colors.RESET}")


if __name__ == "__main__":
    main()
