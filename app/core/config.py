import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()


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

    # Directorios
    REFERENCIAS_DIR = os.getenv("REFERENCIAS_DIR", "referencias")


config = Configuracion()
