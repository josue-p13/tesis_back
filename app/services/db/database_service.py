import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from app.core.config import config
from app.services.obtener.text_utils_service import _normalizar


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
        """Crea las columnas de verificación y normalización si no existen"""
        if not self.connection:
            return
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    ALTER TABLE referencias 
                    ADD COLUMN IF NOT EXISTS fuente_verificacion VARCHAR(100),
                    ADD COLUMN IF NOT EXISTS citaciones INTEGER DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS url_verificada TEXT,
                    ADD COLUMN IF NOT EXISTS fecha_verificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ADD COLUMN IF NOT EXISTS titulo_normalizado TEXT,
                    ADD COLUMN IF NOT EXISTS titulo_original TEXT;
                """)
                self.connection.commit()
        except Exception as e:
            print(f"Nota: Columnas ya existen o error: {e}")
            self.connection.rollback()
    
    def desconectar(self):
        """Cierra la conexión con la base de datos"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def __enter__(self):
        """Permite usar el servicio con context manager.
        Lanza ConnectionError si no se puede conectar, para que el llamador
        sepa que la BD no está disponible y no interprete silencio como 'no encontrado'.
        """
        if not self.conectar():
            raise ConnectionError(
                "No se pudo conectar a la base de datos. "
                "Verifica que PostgreSQL esté activo y que las credenciales en .env sean correctas."
            )
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
        Busca en la BD si ya existe una referencia con título similar.
        Lógica simple:
          1. Toma la primera palabra del título con más de 4 letras.
          2. Busca todos los registros que la contengan (LIKE).
          3. Calcula similitud exacta en Python y retorna el mejor si supera el threshold.
        """
        if not self.connection or not titulo:
            return None

        from app.core.config import config
        from app.services.obtener.text_utils_service import _similitud_titulos, _normalizar

        try:
            titulo_norm = _normalizar(titulo)

            # Primera palabra significativa (>4 letras) para el LIKE
            palabra_clave = next(
                (p for p in titulo_norm.split() if len(p) > 4),
                titulo_norm.split()[0] if titulo_norm.split() else ""
            )
            if not palabra_clave:
                return None

            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM referencias
                    WHERE titulo_normalizado LIKE %s
                       OR LOWER(titulo) LIKE %s
                       OR LOWER(titulo_original) LIKE %s
                       OR LOWER(publicacion) LIKE %s
                    LIMIT 50
                    """,
                    (f"%{palabra_clave}%",) * 4
                )
                candidatos = [dict(r) for r in cursor.fetchall()]

            # Calcular similitud en Python y quedarse con el mejor.
            # Se compara el título buscado contra 'titulo', 'titulo_original' Y 'publicacion'
            # porque Google Scholar a veces guarda el título real del paper en el campo publicacion.
            mejor_match = None
            mejor_sim = 0.0

            for c in candidatos:
                sim = max(
                    _similitud_titulos(titulo, c.get('titulo', '')),
                    _similitud_titulos(titulo, c.get('titulo_original', '') or ''),
                    _similitud_titulos(titulo, c.get('publicacion', '') or ''),
                )
                if sim > mejor_sim and sim >= config.SIMILITUD_TITULO_THRESHOLD:
                    mejor_sim = sim
                    mejor_match = c

            if mejor_match:
                campo_match = (
                    "titulo" if _similitud_titulos(titulo, mejor_match.get('titulo', '')) == mejor_sim
                    else "publicacion" if _similitud_titulos(titulo, mejor_match.get('publicacion', '') or '') == mejor_sim
                    else "titulo_original"
                )
                print(f"[BD] Encontrado por '{campo_match}' (similitud {mejor_sim:.0%}): {mejor_match.get('titulo', '')[:70]}")

            return mejor_match

        except Exception as e:
            print(f"[BD] Error al buscar por título: {e}")
            return None

    def obtener_candidatos_por_autores_y_raw(self, autores: str = "", texto_raw: str = "") -> list:
        """
        Trae candidatos de BD usando autores y/o texto_raw como ancla LIKE.

        No calcula similitud de título aquí — eso lo hace Gemini en el llamador.
        Devuelve lista de dicts (puede ser vacía). Sin duplicados por id.

        Estrategia:
          - Por autores: extrae tokens >3 letras y hace ILIKE en columna 'autores'.
          - Por texto_raw: usa palabras clave del raw (tokens >5 letras, máx 4)
            y hace ILIKE en 'texto_raw' Y en 'autores' (por si el raw tiene apellidos).
        """
        if not self.connection:
            return []
        if not autores and not texto_raw:
            return []

        from app.services.obtener.text_utils_service import _normalizar

        try:
            candidatos_por_id: dict = {}

            with self.connection.cursor() as cursor:

                # ── Por autores ───────────────────────────────────────────────
                if autores:
                    tokens = [t for t in _normalizar(autores).split() if len(t) > 3]
                    for token in tokens[:4]:
                        cursor.execute(
                            "SELECT * FROM referencias WHERE LOWER(autores) LIKE %s LIMIT 50",
                            (f"%{token}%",)
                        )
                        for row in cursor.fetchall():
                            r = dict(row)
                            candidatos_por_id.setdefault(r['id'], r)

                # ── Por texto_raw: palabras clave del raw ─────────────────────
                if texto_raw:
                    tokens_raw = [
                        t for t in _normalizar(texto_raw).split()
                        if len(t) > 5
                    ][:4]
                    for token in tokens_raw:
                        # Buscar en texto_raw guardado en BD
                        cursor.execute(
                            "SELECT * FROM referencias WHERE LOWER(texto_raw) LIKE %s LIMIT 50",
                            (f"%{token}%",)
                        )
                        for row in cursor.fetchall():
                            r = dict(row)
                            candidatos_por_id.setdefault(r['id'], r)

                        # También buscar esa palabra en autores (apellidos en el raw)
                        cursor.execute(
                            "SELECT * FROM referencias WHERE LOWER(autores) LIKE %s LIMIT 50",
                            (f"%{token}%",)
                        )
                        for row in cursor.fetchall():
                            r = dict(row)
                            candidatos_por_id.setdefault(r['id'], r)

            return list(candidatos_por_id.values())

        except Exception as e:
            print(f"[BD] Error al obtener candidatos por autores/raw: {e}")
            return []

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
        titulo_original = referencia.get('titulo_original', '')  # título tal como vino del PDF
        
        # Validar que al menos tenga título
        if not titulo:
            return False, None, "La referencia debe tener al menos un título"
        
        # Calcular título normalizado (del título verificado)
        titulo_normalizado = _normalizar(titulo)
        
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
                     fuente_documento, hash_unico, fuente_verificacion, citaciones, url_verificada,
                     titulo_normalizado, titulo_original)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                        url_verificada,
                        titulo_normalizado,
                        titulo_original or None
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
