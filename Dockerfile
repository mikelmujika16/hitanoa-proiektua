FROM python:3.11-slim

WORKDIR /app

# Instala dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el codigo de la aplicacion
COPY . .

# Railway inyecta la variable PORT automaticamente
EXPOSE 8080

# Un solo worker es suficiente para esta aplicacion
CMD gunicorn -w 1 --timeout 120 -b 0.0.0.0:${PORT:-8080} server:app
