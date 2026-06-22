import os
import pyodbc
from dotenv import load_dotenv

# Cargar variables de entorno desde la raíz del proyecto
# Esto asegura que .env se cargue sin importar desde dónde se ejecute el código
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(dotenv_path=os.path.join(base_dir, '.env'))


def _get_best_odbc_driver() -> str:
    """Detecta el mejor driver ODBC disponible para SQL Server."""
    preferred_drivers = [
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "ODBC Driver 13 for SQL Server",
        "SQL Server Native Client 11.0",
        "SQL Server",  # Driver legacy, siempre disponible en Windows
    ]
    available = pyodbc.drivers()
    for driver in preferred_drivers:
        if driver in available:
            return driver
    raise RuntimeError(
        f"No se encontró ningún driver ODBC para SQL Server. "
        f"Drivers disponibles: {available}"
    )


def get_db_connection():
    """Establece y retorna una conexión a la base de datos SQL Server."""
    DB_HOST = os.getenv("DB_HOST")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_PORT = os.getenv("DB_PORT", "1433")

    driver = _get_best_odbc_driver()

    # Si DB_HOST contiene '\' es una instancia nombrada (ej: eva-01\sql2k8).
    # Las instancias nombradas NO usan SERVER=host,puerto — el puerto lo
    # resuelve automáticamente el servicio SQL Server Browser.
    # Solo se especifica puerto cuando es una IP o nombre de host simple.
    is_named_instance = "\\" in DB_HOST
    if is_named_instance:
        server_str = DB_HOST  # Ej: eva-01\sql2k8
    else:
        server_str = f"{DB_HOST},{DB_PORT}"  # Ej: 192.168.1.10,1433

    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server_str};"
        f"DATABASE={DB_NAME};"
        f"UID={DB_USER};"
        f"PWD={DB_PASSWORD};"
    )

    try:
        conn = pyodbc.connect(connection_string)
        conn.autocommit = True
        return conn
    except Exception as e:
        msg = f"[DB_CONNECTION_ERROR] Driver={driver} | SERVER={server_str} | DB={DB_NAME} | Error: {e}\n"
        print(msg)
        # Escribir también a un archivo de log para verlo aunque stderr esté capturado (modo subprocess MCP)
        try:
            log_path = os.path.join(base_dir, "db_connection_error.log")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(msg)
        except Exception:
            pass
        return "FALLBACK_CSV"

