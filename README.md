# Analizador de Normas Académicas

Backend con FastAPI para analizar documentos PDF y Word según normas APA e IEEE.

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecutar

```bash
python main.py
```

O con uvicorn:

```bash
uvicorn main:app --reload
```

## Uso

La API estará disponible en `http://localhost:8000`

### Endpoints

- `POST /api/analizar/apa` - Analizar documento según normas APA
- `POST /api/analizar/ieee` - Analizar documento según normas IEEE

Enviar el archivo como form-data con el campo `archivo`.

## Estructura

```
back/
├── app/
│   ├── api/          # Rutas de la API
│   ├── modelos/      # Modelos Pydantic
│   ├── servicios/    # Lógica de negocio
│   └── utils/        # Utilidades
├── archivos_temp/    # Almacenamiento temporal
└── main.py           # Punto de entrada
```
