FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Usuario sin privilegios; /app/data es el volumen con la base de datos.
RUN useradd --system --uid 10001 --no-create-home app

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

RUN mkdir -p /app/data && chown -R app:app /app/data

USER app

EXPOSE 8000

# Un solo proceso: el limitador de intentos vive en memoria.
# --forwarded-allow-ips="*" es seguro aquí porque el puerto 8000 no se publica:
# solo Caddy, dentro de la red de Docker, puede llegar a la aplicación.
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
