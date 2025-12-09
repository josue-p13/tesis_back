from pydantic import BaseModel
from enum import Enum

class TipoNorma(str, Enum):
    APA = "apa"
    IEEE = "ieee"

class ResultadoAnalisis(BaseModel):
    cumple: bool
    norma: TipoNorma
    errores: list[str]
    detalles: str
