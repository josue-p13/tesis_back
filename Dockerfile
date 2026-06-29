FROM lfoppiano/grobid:0.8.0

# Cambiar a root para instalar paquetes del sistema
USER root

# Instalar Python 3, pip y herramientas de red
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Asegurar que existe la carpeta tmp de Grobid y tiene los permisos correctos para el usuario 1000
RUN mkdir -p /opt/grobid/grobid-home/tmp && chown -R 1000:1000 /opt/grobid/grobid-home/tmp

# Crear el directorio de trabajo y asegurar permisos para el usuario 1000 (grobid)
WORKDIR /app
RUN chown -R 1000:1000 /app

# Cambiar al usuario 1000 de Hugging Face para ejecutar el contenedor de forma segura
USER 1000

# Configurar el entorno virtual en una ruta propiedad del usuario 1000
ENV VIRTUAL_ENV=/app/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copiar archivos de dependencias
COPY --chown=1000:1000 requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del backend
COPY --chown=1000:1000 . .

# Exponer el puerto requerido por Hugging Face Spaces
EXPOSE 7860

# Dar permisos de ejecución al script de arranque
RUN chmod +x entrypoint.sh

# Comando de arranque del contenedor
CMD ["/bin/bash", "entrypoint.sh"]
