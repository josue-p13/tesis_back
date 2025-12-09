import pypdf
from docx import Document
from pathlib import Path

def extraer_texto_pdf(ruta_archivo: str) -> str:
    texto = ""
    with open(ruta_archivo, 'rb') as archivo:
        lector_pdf = pypdf.PdfReader(archivo)
        for pagina in lector_pdf.pages:
            texto += pagina.extract_text()
    return texto

def extraer_texto_word(ruta_archivo: str) -> str:
    documento = Document(ruta_archivo)
    texto = ""
    for parrafo in documento.paragraphs:
        texto += parrafo.text + "\n"
    return texto

def extraer_texto(ruta_archivo: str) -> str:
    extension = Path(ruta_archivo).suffix.lower()
    
    if extension == '.pdf':
        return extraer_texto_pdf(ruta_archivo)
    elif extension in ['.docx', '.doc']:
        return extraer_texto_word(ruta_archivo)
    else:
        raise ValueError(f"Formato no soportado: {extension}")
