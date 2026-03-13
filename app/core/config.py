import os
from dotenv import load_dotenv

# override=True garantiza que el .env SIEMPRE gana sobre variables del sistema,
# evitando que sesiones anteriores de terminal o Docker sobrescriban los valores.
load_dotenv(override=True)


class Configuracion:
    """Configuración de la aplicación"""
    
    # Base de datos
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_USER = os.getenv("DB_USER", "referencias_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "referencias_pass")
    DB_NAME = os.getenv("DB_NAME", "referencias_db")
    
    # URL de conexión a PostgreSQL
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # GROBID
    GROBID_URL = os.getenv("GROBID_URL", "http://localhost:8070")

    # APIs externas
    CORE_API_KEY = os.getenv("CORE_API_KEY", "")
    
    # Serper.dev (Google Scholar API)
    # USAR_SERPER se lee exclusivamente del .env — no hay default en código.
    # Si la variable no existe en .env, queda False (desactivado).
    SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
    USAR_SERPER = os.getenv("USAR_SERPER", "").strip().lower() in ("true", "1", "yes")

    # Directorios
    REFERENCIAS_DIR = os.getenv("REFERENCIAS_DIR", "referencias")

    # Validación y similitud
    SIMILITUD_TITULO_THRESHOLD = float(os.getenv("SIMILITUD_TITULO_THRESHOLD", "0.85"))


config = Configuracion()

# Log de arranque para confirmar valores críticos
print(f"[CONFIG] USAR_SERPER={config.USAR_SERPER} | "
      f"SIMILITUD_THRESHOLD={config.SIMILITUD_TITULO_THRESHOLD}")
