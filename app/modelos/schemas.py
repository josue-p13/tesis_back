from pydantic import BaseModel
from enum import Enum
from typing import List, Optional

class TipoNorma(str, Enum):
    APA = "apa"
    HARVARD = "harvard"
    IEEE = "ieee"

class CitaDetalle(BaseModel):
    texto: str
    valida: bool

class ResultadoAnalisis(BaseModel):
    cumple: bool
    norma: TipoNorma
    errores: list[str]
    detalles: str
    citas_validas: List[CitaDetalle] = []
    total_citas: int = 0
    archivo_reporte: Optional[str] = None
    referencias_completas: List[str] = []
    estilo_detectado: Optional[str] = None
