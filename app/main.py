from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers.document_controller import router as document_router


def crear_aplicacion() -> FastAPI:
    app = FastAPI(
        title="Sistema de Extracción de Referencias", 
        version="1.0.0",
        description="Extrae referencias bibliográficas de PDFs usando GROBID"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(document_router, prefix="/documents", tags=["Documentos"])
    return app


app = crear_aplicacion()
