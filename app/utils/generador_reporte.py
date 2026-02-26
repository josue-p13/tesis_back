from datetime import datetime
from pathlib import Path
from app.modelos.schemas import ResultadoAnalisis
from typing import List, Dict, Any
import os

def generar_reporte_txt(resultado: ResultadoAnalisis, nombre_archivo: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_reporte = f"reporte_{nombre_archivo}_{timestamp}_original.txt"
    ruta_reporte = Path("archivos_temp") / nombre_reporte
    
    with open(ruta_reporte, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("REPORTE DE ANÁLISIS DE NORMAS ACADÉMICAS\n")
        f.write("="*70 + "\n\n")
        
        f.write(f"Archivo analizado: {nombre_archivo}\n")
        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        if resultado.estilo_detectado:
            f.write(f"Estilo detectado: {resultado.estilo_detectado}\n")
        f.write(f"Norma evaluada: {resultado.norma.value.upper()}\n")
        f.write(f"Resultado: {'✓ CUMPLE' if resultado.cumple else '✗ NO CUMPLE'}\n")
        f.write("\n" + "-"*70 + "\n\n")
        
        f.write(f"RESUMEN:\n")
        f.write(f"{resultado.detalles}\n\n")
        
        if resultado.errores:
            f.write("ERRORES ENCONTRADOS:\n")
            for i, error in enumerate(resultado.errores, 1):
                f.write(f"  {i}. {error}\n")
            f.write("\n")
        
        f.write("-"*70 + "\n")
        f.write(f"REFERENCIAS EXTRAÍDAS DEL DOCUMENTO\n")
        f.write("-"*70 + "\n\n")
        
        f.write(f"Total de referencias: {len(resultado.citas_validas)}\n\n")
        
        if resultado.citas_validas:
            for i, cita in enumerate(resultado.citas_validas, 1):
                f.write(f"{i}. {cita.texto}\n\n")
        else:
            f.write("No se encontraron referencias en el documento.\n\n")
        
        f.write("="*70 + "\n")
        f.write("FIN DEL REPORTE\n")
        f.write("="*70 + "\n")
    
    return str(ruta_reporte)

def generar_reporte_estructurado(referencias_estructuradas: List[Dict[str, Any]], nombre_archivo: str) -> str:
    """Genera el segundo archivo TXT con referencias estructuradas por GROBID"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_reporte = f"reporte_{nombre_archivo}_{timestamp}_estructurado.txt"
    ruta_reporte = Path("archivos_temp") / nombre_reporte
    
    # Separar exitosas y fallidas
    exitosas = [r for r in referencias_estructuradas if r.get("status") == "success"]
    fallidas = [r for r in referencias_estructuradas if r.get("status") == "error"]
    
    lineas = []
    lineas.append("=" * 70)
    lineas.append("REFERENCIAS ESTRUCTURADAS POR GROBID")
    lineas.append("=" * 70)
    lineas.append("")
    lineas.append(f"Archivo analizado: {nombre_archivo}")
    lineas.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lineas.append(f"Total de referencias procesadas: {len(referencias_estructuradas)}")
    lineas.append(f"Referencias estructuradas exitosamente: {len(exitosas)}")
    lineas.append(f"Referencias con errores: {len(fallidas)}")
    lineas.append("")
    lineas.append("-" * 70)
    
    # Sección de referencias exitosas
    if exitosas:
        lineas.append("")
        lineas.append("REFERENCIAS ESTRUCTURADAS EXITOSAMENTE")
        lineas.append("-" * 70)
        lineas.append("")
        
        for i, ref in enumerate(exitosas, 1):
            lineas.append(f"REFERENCIA #{i}")
            lineas.append("-" * 70)
            
            # Autores
            autores = ref.get("autores", [])
            if autores:
                lineas.append(f"Autores: {', '.join(autores)}")
            
            # Título
            titulo = ref.get("titulo")
            if titulo:
                lineas.append(f"Título: {titulo}")
            
            # Año
            anio = ref.get("año")
            if anio:
                lineas.append(f"Año: {anio}")
            
            # Revista
            revista = ref.get("revista")
            if revista:
                lineas.append(f"Revista/Journal: {revista}")
            
            # Volumen
            volumen = ref.get("volumen")
            if volumen:
                lineas.append(f"Volumen: {volumen}")
            
            # Número
            numero = ref.get("numero")
            if numero:
                lineas.append(f"Número: {numero}")
            
            # Páginas
            paginas = ref.get("paginas")
            if paginas:
                lineas.append(f"Páginas: {paginas}")
            
            # DOI
            doi = ref.get("doi")
            if doi:
                lineas.append(f"DOI: {doi}")
            
            # Editorial
            editorial = ref.get("editorial")
            if editorial:
                lineas.append(f"Editorial: {editorial}")
            
            # Ciudad
            ciudad = ref.get("ciudad")
            if ciudad:
                lineas.append(f"Ciudad: {ciudad}")
            
            # Tipo
            tipo = ref.get("tipo")
            if tipo:
                lineas.append(f"Tipo: {tipo}")
            
            # Texto original
            lineas.append("")
            lineas.append("Texto original:")
            lineas.append(f"{ref.get('texto_original', 'N/A')}")
            lineas.append("")
    
    # Sección de referencias con errores
    if fallidas:
        lineas.append("")
        lineas.append("REFERENCIAS CON ERRORES AL ESTRUCTURAR")
        lineas.append("-" * 70)
        lineas.append("")
        
        for i, ref in enumerate(fallidas, 1):
            lineas.append(f"REFERENCIA CON ERROR #{i}")
            lineas.append("-" * 70)
            lineas.append(f"Motivo: {ref.get('motivo', 'Desconocido')}")
            lineas.append("Texto original:")
            lineas.append(f"{ref.get('texto_original', 'N/A')}")
            lineas.append("")
    
    lineas.append("=" * 70)
    lineas.append("FIN DEL REPORTE ESTRUCTURADO")
    lineas.append("=" * 70)
    
    with open(ruta_reporte, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))
    
    print(f"[REPORTE] Archivo estructurado generado: {ruta_reporte}")
    print(f"[REPORTE] Exitosas: {len(exitosas)}, Fallidas: {len(fallidas)}")
    
    return str(ruta_reporte)

def generar_reporte_estructurado(referencias_estructuradas: List[Dict[str, Any]], nombre_archivo: str) -> str:
    """Genera el segundo archivo TXT con referencias estructuradas por GROBID"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_reporte = f"reporte_{nombre_archivo}_{timestamp}_estructurado.txt"
    ruta_reporte = Path("archivos_temp") / nombre_reporte
    
    with open(ruta_reporte, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("REFERENCIAS ESTRUCTURADAS POR GROBID\n")
        f.write("="*70 + "\n\n")
        
        f.write(f"Archivo analizado: {nombre_archivo}\n")
        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total de referencias procesadas: {len(referencias_estructuradas)}\n\n")
        f.write("-"*70 + "\n\n")
        
        for i, ref in enumerate(referencias_estructuradas, 1):
            f.write(f"REFERENCIA #{i}\n")
            f.write("-"*70 + "\n")
            
            if ref.get("status") == "success":
                # Autores
                autores = ref.get("autores", [])
                if autores:
                    f.write(f"Autores: {', '.join(autores)}\n")
                else:
                    f.write("Autores: No detectados\n")
                
                # Título
                titulo = ref.get("titulo")
                f.write(f"Título: {titulo if titulo else 'No detectado'}\n")
                
                # Año
                año = ref.get("año")
                f.write(f"Año: {año if año else 'No detectado'}\n")
                
                # Revista (si existe)
                revista = ref.get("revista")
                if revista:
                    f.write(f"Revista: {revista}\n")
                
                # Volumen (si existe)
                volumen = ref.get("volumen")
                if volumen:
                    f.write(f"Volumen: {volumen}\n")
                
                # Páginas (si existe)
                paginas = ref.get("paginas")
                if paginas:
                    f.write(f"Páginas: {paginas}\n")
                
                # DOI (si existe)
                doi = ref.get("doi")
                if doi:
                    f.write(f"DOI: {doi}\n")
                
                # Editorial (si existe)
                editorial = ref.get("editorial")
                if editorial:
                    f.write(f"Editorial: {editorial}\n")
                
                # Ciudad (si existe)
                ciudad = ref.get("ciudad")
                if ciudad:
                    f.write(f"Ciudad: {ciudad}\n")
                
                # Texto original
                f.write(f"\nTexto original:\n{ref.get('texto_original', 'N/A')}\n")
                
            else:
                f.write("ERROR: No se pudo estructurar esta referencia\n")
                texto_orig = ref.get("texto_original")
                if texto_orig:
                    f.write(f"Texto original: {texto_orig}\n")
                error = ref.get("error") or ref.get("message")
                if error:
                    f.write(f"Motivo: {error}\n")
            
            f.write("\n")
        
        f.write("="*70 + "\n")
        f.write("FIN DEL REPORTE ESTRUCTURADO\n")
        f.write("="*70 + "\n")
    
    print(f"[REPORTE] Archivo estructurado generado: {ruta_reporte}")
    return str(ruta_reporte)
