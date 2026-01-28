from pydantic import BaseModel
from enum import Enum
from typing import List, Optional

class TipoNorma(str, Enum):
    APA = "apa"
    IEEE = "ieee"

class CitaDetalle(BaseModel):
    texto: str
    valida: bool
    razon: Optional[str] = None
    texto_completo: Optional[str] = None  # Texto original completo de la referencia

class ResultadoAnalisis(BaseModel):
    cumple: bool
    norma: TipoNorma
    errores: list[str]
    detalles: str
    citas_validas: List[CitaDetalle] = []
    citas_invalidas: List[CitaDetalle] = []
    total_citas: int = 0
    archivo_reporte: Optional[str] = None
    referencias_completas: List[str] = []  # Texto completo de TODAS las referencias extraídas
