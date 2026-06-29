# Servicios de verificación y validación de referencias
from app.services.verificador import (
    api_openalex_service,
    api_crossref_service,
    api_semanticscholar_service,
    api_pubmed_service,
    api_core_service,
    api_googlebooks_service,
)
from app.services.verificador.validacion_referencias_service import validar_referencias, cerrar_cliente

__all__ = [
    'api_openalex_service',
    'api_crossref_service',
    'api_semanticscholar_service',
    'api_pubmed_service',
    'api_core_service',
    'api_googlebooks_service',
    'validar_referencias',
    'cerrar_cliente',
]
