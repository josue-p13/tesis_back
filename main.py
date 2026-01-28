from fastapi import FastAPI
from app.api import rutas

app = FastAPI(title="Analizador de Normas Académicas")

app.include_router(rutas.router)

@app.get("/")
def raiz():
    return {"mensaje": "API de análisis de normas APA e IEEE"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)