import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from app.core.config import config


class DatabaseService:
    """Servicio para manejar operaciones de base de datos"""
    
    def __init__(self):
        self.connection = None
    
    def conectar(self):
        """Establece conexión con la base de datos"""
        try:
            self.connection = psycopg2.connect(
                host=config.DB_HOST,
                port=config.DB_PORT,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                dbname=config.DB_NAME,
                cursor_factory=RealDictCursor
            )
            # Crear columnas nuevas si no existen (migración automática)
            self._crear_columnas_verificacion()
            return True
        except Exception as e:
            print(f"Error al conectar a la base de datos: {e}")
            return False
    
    def _crear_columnas_verificacion(self):
        """Crea las columnas de verificación si no existen"""
        if not self.connection:
            return
        
        try:
            with self.connection.cursor() as cursor:
                # Agregar columnas para datos de verificación
                cursor.execute("""
                    ALTER TABLE referencias 
                    ADD COLUMN IF NOT EXISTS fuente_verificacion VARCHAR(100),
                    ADD COLUMN IF NOT EXISTS citaciones INTEGER DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS url_verificada TEXT,
                    ADD COLUMN IF NOT EXISTS fecha_verificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                """)
                self.connection.commit()
        except Exception as e:
            print(f"Nota: Columnas de verificación ya existen o error: {e}")
            self.connection.rollback()
    
    def desconectar(self):
        """Cierra la conexión con la base de datos"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def __enter__(self):
        """Permite usar el servicio con context manager"""
        self.conectar()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cierra la conexión al salir del context manager"""
        self.desconectar()
    
    @staticmethod
    def calcular_hash_referencia(titulo: str, autores: str = "", año: str = "", publicacion: str = "") -> str:
        """
        Calcula un hash único para una referencia basándose en los campos importantes.
        Excluye volumen y páginas para hacer la verificación más global.
        
        Args:
            titulo: Título de la publicación
            autores: Autores (pueden estar en distintos formatos)
            año: Año de publicación
            publicacion: Nombre de la publicación/revista
            
        Returns:
            Hash MD5 en hexadecimal
        """
        # Normalizar los campos para la comparación
        titulo_norm = titulo.lower().strip() if titulo else ""
        autores_norm = autores.lower().strip() if autores else ""
        año_norm = año.strip() if año else ""
        publicacion_norm = publicacion.lower().strip() if publicacion else ""
        
        # Crear string único con los campos importantes
        cadena_unica = f"{titulo_norm}|{autores_norm}|{año_norm}|{publicacion_norm}"
        
        # Calcular hash MD5
        return hashlib.md5(cadena_unica.encode('utf-8')).hexdigest()
    
    def verificar_duplicado(self, titulo: str, autores: str = "", año: str = "", 
                           publicacion: str = "") -> Tuple[bool, Optional[Dict]]:
        """
        Verifica si una referencia ya existe en la base de datos.
        
        Args:
            titulo: Título de la publicación
            autores: Autores
            año: Año de publicación
            publicacion: Nombre de la publicación
            
        Returns:
            Tupla (es_duplicado: bool, referencia_existente: Dict o None)
        """
        if not self.connection:
            raise Exception("No hay conexión a la base de datos")
        
        hash_unico = self.calcular_hash_referencia(titulo, autores, año, publicacion)
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM referencias 
                    WHERE hash_unico = %s
                    LIMIT 1
                    """,
                    (hash_unico,)
                )
                resultado = cursor.fetchone()
                
                if resultado:
                    return True, dict(resultado)
                return False, None
                
        except Exception as e:
            print(f"Error al verificar duplicado: {e}")
            return False, None
    
    def buscar_por_doi(self, doi: str) -> Optional[Dict]:
        """
        Busca una referencia en la BD por DOI exacto.
        
        Args:
            doi: DOI a buscar
            
        Returns:
            Diccionario con la referencia si existe, None si no
        """
        if not self.connection or not doi:
            return None
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM referencias 
                    WHERE doi = %s
                    LIMIT 1
                    """,
                    (doi.strip(),)
                )
                resultado = cursor.fetchone()
                return dict(resultado) if resultado else None
                
        except Exception as e:
            print(f"Error al buscar por DOI: {e}")
            return None
    
    def buscar_por_titulo_similitud(self, titulo: str, autores: str = "") -> Optional[Dict]:
        """
        Busca una referencia en la BD por similitud de título.
        Usa el threshold configurado en config.py
        
        Args:
            titulo: Título a buscar
            autores: Autores (opcional, mejora precisión)
            
        Returns:
            Diccionario con la referencia si existe y supera el threshold, None si no
        """
        if not self.connection or not titulo:
            return None
        
        from app.core.config import config
        from app.services.obtener.text_utils_service import _similitud_titulos
        
        try:
            with self.connection.cursor() as cursor:
                # Buscar candidatos por título similar (búsqueda amplia)
                cursor.execute(
                    """
                    SELECT * FROM referencias 
                    WHERE titulo ILIKE %s
                    LIMIT 10
                    """,
                    (f"%{titulo[:50]}%",)
                )
                candidatos = [dict(row) for row in cursor.fetchall()]
                
                # Si hay autores, también buscar por autores
                if autores and not candidatos:
                    cursor.execute(
                        """
                        SELECT * FROM referencias 
                        WHERE autores ILIKE %s
                        LIMIT 10
                        """,
                        (f"%{autores[:30]}%",)
                    )
                    candidatos.extend([dict(row) for row in cursor.fetchall()])
                
                # Calcular similitud y encontrar el mejor match
                mejor_match = None
                mejor_similitud = 0.0
                
                for candidato in candidatos:
                    similitud = _similitud_titulos(titulo, candidato.get('titulo', ''))
                    
                    # Si hay autores, dar peso adicional si coinciden
                    if autores and candidato.get('autores'):
                        autores_similar = _similitud_titulos(autores, candidato['autores'])
                        similitud = (similitud * 0.7) + (autores_similar * 0.3)
                    
                    if similitud > mejor_similitud and similitud >= config.SIMILITUD_TITULO_THRESHOLD:
                        mejor_similitud = similitud
                        mejor_match = candidato
                
                return mejor_match
                
        except Exception as e:
            print(f"Error al buscar por título: {e}")
            return None
    
    def guardar_referencia(self, referencia: Dict, fuente_documento: str = "", 
                          datos_verificacion: Optional[Dict] = None) -> Tuple[bool, Optional[int], str]:
        """
        Guarda una referencia en la base de datos si no existe.
        
        Args:
            referencia: Diccionario con los datos de la referencia
            fuente_documento: Nombre del documento fuente
            datos_verificacion: Datos de verificación (fuente, citaciones, url_verificada)
            
        Returns:
            Tupla (guardado: bool, id: int o None, mensaje: str)
        """
        if not self.connection:
            raise Exception("No hay conexión a la base de datos")
        
        # Extraer campos
        titulo = referencia.get('titulo', '')
        autores = referencia.get('autores', '')
        año = referencia.get('año', '')
        publicacion = referencia.get('publicacion', '')
        
        # Validar que al menos tenga título
        if not titulo:
            return False, None, "La referencia debe tener al menos un título"
        
        # Verificar duplicado
        es_duplicado, ref_existente = self.verificar_duplicado(titulo, autores, año, publicacion)
        
        if es_duplicado:
            return False, ref_existente['id'], f"Referencia duplicada (ID: {ref_existente['id']})"
        
        # Calcular hash único
        hash_unico = self.calcular_hash_referencia(titulo, autores, año, publicacion)
        
        # Extraer datos de verificación si existen
        fuente_verificacion = None
        citaciones = 0
        url_verificada = None
        
        if datos_verificacion:
            fuente_verificacion = datos_verificacion.get('fuente')
            citaciones = datos_verificacion.get('citaciones', 0)
            url_verificada = datos_verificacion.get('url')
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO referencias 
                    (titulo, autores, año, publicacion, doi, volumen, paginas, texto_raw, 
                     fuente_documento, hash_unico, fuente_verificacion, citaciones, url_verificada)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        titulo,
                        autores,
                        año,
                        publicacion,
                        referencia.get('doi', None),
                        referencia.get('volumen', None),
                        referencia.get('paginas', None),
                        referencia.get('raw', None),
                        fuente_documento,
                        hash_unico,
                        fuente_verificacion,
                        citaciones,
                        url_verificada
                    )
                )
                
                nueva_id = cursor.fetchone()['id']
                self.connection.commit()
                
                return True, nueva_id, f"Referencia guardada exitosamente (ID: {nueva_id})"
                
        except Exception as e:
            self.connection.rollback()
            print(f"Error al guardar referencia: {e}")
            return False, None, f"Error al guardar: {str(e)}"
    
    def guardar_multiples_referencias(self, referencias: List[Dict], 
                                     fuente_documento: str = "") -> Dict[str, any]:
        """
        Guarda múltiples referencias en la base de datos.
        
        Args:
            referencias: Lista de referencias a guardar
            fuente_documento: Nombre del documento fuente
            
        Returns:
            Diccionario con estadísticas del proceso
        """
        if not self.connection:
            raise Exception("No hay conexión a la base de datos")
        
        resultados = {
            'total': len(referencias),
            'guardadas': 0,
            'duplicadas': 0,
            'errores': 0,
            'detalles': []
        }
        
        for idx, ref in enumerate(referencias, 1):
            guardado, ref_id, mensaje = self.guardar_referencia(ref, fuente_documento)
            
            detalle = {
                'numero': idx,
                'titulo': ref.get('titulo', 'Sin título')[:50],
                'guardado': guardado,
                'id': ref_id,
                'mensaje': mensaje
            }
            
            if guardado:
                resultados['guardadas'] += 1
            elif 'duplicada' in mensaje.lower():
                resultados['duplicadas'] += 1
            else:
                resultados['errores'] += 1
            
            resultados['detalles'].append(detalle)
        
        return resultados
    
    def buscar_referencias(self, query: str = "", limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Busca referencias en la base de datos.
        
        Args:
            query: Texto a buscar (busca en título, autores y publicación)
            limit: Número máximo de resultados
            offset: Offset para paginación
            
        Returns:
            Lista de referencias encontradas
        """
        if not self.connection:
            raise Exception("No hay conexión a la base de datos")
        
        try:
            with self.connection.cursor() as cursor:
                if query:
                    # Búsqueda con texto
                    cursor.execute(
                        """
                        SELECT * FROM referencias
                        WHERE titulo ILIKE %s 
                           OR autores ILIKE %s 
                           OR publicacion ILIKE %s
                        ORDER BY fecha_creacion DESC
                        LIMIT %s OFFSET %s
                        """,
                        (f"%{query}%", f"%{query}%", f"%{query}%", limit, offset)
                    )
                else:
                    # Obtener todas las referencias
                    cursor.execute(
                        """
                        SELECT * FROM referencias
                        ORDER BY fecha_creacion DESC
                        LIMIT %s OFFSET %s
                        """,
                        (limit, offset)
                    )
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            print(f"Error al buscar referencias: {e}")
            return []
    
    def obtener_estadisticas(self) -> Dict:
        """
        Obtiene estadísticas de las referencias almacenadas.
        
        Returns:
            Diccionario con estadísticas
        """
        if not self.connection:
            raise Exception("No hay conexión a la base de datos")
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT * FROM estadisticas_referencias")
                stats = cursor.fetchone()
                return dict(stats) if stats else {}
                
        except Exception as e:
            print(f"Error al obtener estadísticas: {e}")
            return {}
