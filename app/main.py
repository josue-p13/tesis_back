from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import config
from app.controllers.document_controller import router as document_router
from app.controllers.auth_controller import router as auth_router


def crear_aplicacion() -> FastAPI:
    app = FastAPI(
        title="Sistema de Extracción de Referencias", 
        version="1.0.0",
        description="Extrae referencias bibliográficas de PDFs usando GROBID"
    )

    # Middleware de sesión para Google OAuth
    app.add_middleware(
        SessionMiddleware, 
        secret_key=config.SECRET_KEY
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(document_router, prefix="/documents", tags=["Documentos"])
    app.include_router(auth_router, prefix="", tags=["Autenticación"])
    return app


app = crear_aplicacion()
