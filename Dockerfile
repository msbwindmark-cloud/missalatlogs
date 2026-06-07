# Usamos una imagen de Python ligera
FROM python:3.11-slim

# Evitar que Python genere archivos .pyc y habilitar logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias para PostgreSQL, Pillow y PDF
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff5-dev \
    tk-dev \
    tcl-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del proyecto
COPY . /app/

# Crear carpetas para estáticos y media
RUN mkdir -p /app/static /app/media/intruders

# Recopilar archivos estáticos
RUN python manage.py collectstatic --noinput

# Exponer el puerto que usa Hugging Face Spaces
EXPOSE 7860

# Comando para arrancar la aplicación con Gunicorn
# Ajustado para usar el puerto 7860 y permitir acceso externo
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:7860", "--workers", "3"]
