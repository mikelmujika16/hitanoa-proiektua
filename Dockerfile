FROM python:3.11-slim

WORKDIR /app

# Instala dependencias del sistema necesarias para compilar paquetes Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Instala dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-descarga el modelo de Stanza para euskera durante la construccion de la imagen
# Esto evita la descarga en cada arranque del contenedor
ENV STANZA_RESOURCES_DIR=/app/stanza_resources
RUN python -c "import stanza; stanza.download('eu', processors='tokenize,pos,lemma', verbose=False)"

# Copia el codigo de la aplicacion
COPY . .

# Railway inyecta la variable PORT automaticamente
EXPOSE 8080

# Un solo worker para no multiplicar el uso de memoria del modelo Stanza
CMD gunicorn -w 1 --timeout 120 -b 0.0.0.0:${PORT:-8080} server:app
