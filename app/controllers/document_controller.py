from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import Any, Dict, List

from app.services.obtener.document_service import extraer_referencias_grobid
from app.services.obtener.citation_style_detector_service import detectar_estilo_citacion, obtener_descripcion_estilo
from app.services.verificador.validacion_referencias_service import validar_referencias


router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# POST /documents/extraer
# Recibe: PDF + serper_api_key + usar_serper
# Devuelve: referencias extraídas del PDF + estilo de citación
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/extraer")
async def extraer_referencias(
    pdf: UploadFile = File(..., description="Archivo PDF a procesar"),
    serper_api_key: str = Form("", description="API Key de Serper.dev (opcional)"),
    usar_serper: bool = Form(False, description="Activar búsqueda en Google Scholar via Serper"),
) -> Dict[str, Any]:
    """
    Extrae las referencias bibliográficas de un PDF usando GROBID.

    - Recibe el PDF como multipart/form-data.
    - Devuelve las referencias crudas extraídas y el estilo de citación detectado.
    - serper_api_key y usar_serper se guardan en la respuesta para que el front
      los reenvíe al endpoint /validar sin necesidad de pedírselos de nuevo al usuario.
    """
    if pdf.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="El archivo debe ser un PDF (content-type: application/pdf)"
        )

    try:
        referencias_extraidas, _ = await extraer_referencias_grobid(pdf, guardar_en_bd=False)

        estilo_citacion = detectar_estilo_citacion(referencias_extraidas)
        descripcion_estilo = obtener_descripcion_estilo(estilo_citacion)

        return {
            "total_referencias": len(referencias_extraidas),
            "estilo_citacion": {
                "nombre": estilo_citacion,
                "descripcion": descripcion_estilo,
            },
            "referencias": referencias_extraidas,
            # Devolvemos los parámetros de Serper para que el front los reenvíe a /validar
            "serper_api_key": serper_api_key,
            "usar_serper": usar_serper,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el PDF: {str(e)}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# POST /documents/validar
# Recibe: lista de referencias (JSON) + serper_api_key + usar_serper
# Devuelve: resultado completo de validación por cada referencia
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/validar")
async def validar_referencias_endpoint(
    body: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Valida las referencias contra APIs académicas externas.

    Body JSON esperado:
    {
        "referencias": [...],       // lista de referencias obtenidas de /extraer
        "serper_api_key": "...",    // API Key de Serper.dev (string, puede ser "")
        "usar_serper": true/false   // si se debe usar Google Scholar como último recurso
    }

    Devuelve el resultado de la validación: estado por referencia, fuente, DOI encontrado, etc.
    """
    referencias: List[Dict] = body.get("referencias", [])
    serper_api_key: str = body.get("serper_api_key", "")
    usar_serper: bool = bool(body.get("usar_serper", False))

    if not referencias:
        raise HTTPException(
            status_code=400,
            detail="El campo 'referencias' es obligatorio y no puede estar vacío"
        )

    try:
        resultado = await validar_referencias(
            referencias,
            serper_api_key=serper_api_key,
            usar_serper=usar_serper,
        )
        return resultado

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al validar las referencias: {str(e)}"
        )
