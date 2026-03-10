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
            return True
        except Exception as e:
            print(f"Error al conectar a la base de datos: {e}")
            return False
    
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
    
    def guardar_referencia(self, referencia: Dict, fuente_documento: str = "") -> Tuple[bool, Optional[int], str]:
        """
        Guarda una referencia en la base de datos si no existe.
        
        Args:
            referencia: Diccionario con los datos de la referencia
            fuente_documento: Nombre del documento fuente
            
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
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO referencias 
                    (titulo, autores, año, publicacion, doi, volumen, paginas, texto_raw, fuente_documento, hash_unico)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                        hash_unico
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
