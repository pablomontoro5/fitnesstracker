# Etapa 1: compila la interfaz de Angular (frontend-angular/). El resultado va a
# /build/app/frontend-ng (outputPath de angular.json) y se copia a la imagen final.
FROM node:24-slim AS angular-build

WORKDIR /build/frontend-angular

COPY frontend-angular/package.json frontend-angular/package-lock.json ./
RUN npm ci

COPY frontend-angular ./
RUN npx ng build


# Etapa 2: la aplicación (FastAPI), que sirve también lo compilado en /app/.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Usuario sin privilegios.
RUN useradd --system --uid 10001 --no-create-home app

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY --from=angular-build /build/app/frontend-ng ./app/frontend-ng

USER app

EXPOSE 8000

# Un solo proceso: el limitador de intentos vive en memoria.
# --forwarded-allow-ips="*" es seguro aquí porque el puerto 8000 no se publica:
# solo Caddy, dentro de la red de Docker, puede llegar a la aplicación.
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
