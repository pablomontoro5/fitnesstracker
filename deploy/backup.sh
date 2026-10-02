#!/usr/bin/env bash
# Copia nocturna: genera una copia SQLite verificada dentro del contenedor, la
# cifra con age y la sube al almacenamiento remoto con rclone.
# La copia viaja por una tubería: nunca se guarda sin cifrar en el servidor.
#
# Configuración en el archivo indicado por BACKUP_ENV (por defecto
# /etc/fitness-tracker/backup.env). Ver docs/DEPLOY.md.
set -euo pipefail

ENV_FILE="${BACKUP_ENV:-/etc/fitness-tracker/backup.env}"
# shellcheck disable=SC1090
source "$ENV_FILE"

: "${COMPOSE_DIR:?Falta COMPOSE_DIR en $ENV_FILE}"
: "${AGE_RECIPIENT:?Falta AGE_RECIPIENT (clave pública age) en $ENV_FILE}"
: "${RCLONE_REMOTE:?Falta RCLONE_REMOTE (p. ej. b2:mi-bucket/fitness) en $ENV_FILE}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

name="fitness_tracker_$(date -u +%Y-%m-%dT%H-%M-%SZ).db.age"

# Se sube con extensión .partial y solo se renombra si toda la tubería ha ido
# bien; así una copia truncada nunca parece una copia válida.
docker compose --project-directory "$COMPOSE_DIR" exec -T app \
    python -m app.cli backup --stdout \
  | age -r "$AGE_RECIPIENT" \
  | rclone rcat "$RCLONE_REMOTE/$name.partial"

rclone moveto "$RCLONE_REMOTE/$name.partial" "$RCLONE_REMOTE/$name"

# La limpieza va después de la subida: si la copia falla, el script termina
# antes y no se borra nada.
rclone delete "$RCLONE_REMOTE" \
    --min-age "${RETENTION_DAYS}d" \
    --include "fitness_tracker_*.db.age"
rclone delete "$RCLONE_REMOTE" --min-age 2d --include "*.partial"

# Aviso opcional de «latido» (por ejemplo healthchecks.io): si dejas de recibirlo,
# el servicio te avisa de que las copias han dejado de hacerse.
if [[ -n "${HEALTHCHECK_URL:-}" ]]; then
    curl -fsS --retry 3 -o /dev/null "$HEALTHCHECK_URL" || true
fi

echo "Copia subida: $RCLONE_REMOTE/$name"
