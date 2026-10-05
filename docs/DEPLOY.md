# Despliegue en un servidor (VPS + Docker + Caddy)

Guía paso a paso para publicar la aplicación con HTTPS, usuarios reales y copias
de seguridad cifradas fuera del servidor. Pensada para pocos usuarios (unos 5 al
empezar). La aplicación (FastAPI) corre en un servidor propio; los datos viven en
una base **PostgreSQL de Supabase**. Supabase se usa solo como base de datos: la
autenticación sigue siendo la de la aplicación.

```
Internet ──443──▶ Caddy (HTTPS automático) ──▶ FastAPI (contenedor "app")
                                                   │  (PostgreSQL por SSL)
                                                   ▼
                                           Supabase (PostgreSQL, región UE)
                                                   ▲
   copia nocturna: pg_dump ──▶ age (cifrado) ──▶ rclone ──▶ almacenamiento externo (S3/B2)
```

## 0. Qué necesitas

| Cosa | Para qué | Coste orientativo |
| --- | --- | --- |
| Un VPS en la UE (p. ej. Hetzner Cloud, plan más pequeño, Ubuntu 24.04) | Ejecutar la app | Unos pocos euros al mes. **Comprueba el precio actual**: Hetzner subió tarifas en 2026 |
| Un proyecto de Supabase en la UE | Base de datos PostgreSQL | Plan gratuito para empezar. **Comprueba en su página de precios** qué incluye: los proyectos gratuitos se pausan tras un tiempo sin actividad y no garantizan copias propias, por eso mantenemos la copia nocturna cifrada |
| Un dominio | HTTPS con certificado propio | ≈10 €/año |
| Una cuenta de almacenamiento S3 compatible (p. ej. Backblaze B2) | Guardar las copias fuera del servidor | Céntimos al mes con una base de datos pequeña |

Contratar el servidor, comprar el dominio y crear las cuentas de Supabase y de almacenamiento (pasos 1, 2, 3b y 6.2) solo puedes hacerlo tú.

## 1. Servidor

1. Crea una clave SSH en tu ordenador si no tienes (Git Bash):
   ```bash
   ssh-keygen -t ed25519 -C "fitness-tracker"
   cat ~/.ssh/id_ed25519.pub     # esto es lo que subes al proveedor
   ```
2. En el proveedor crea un servidor: Ubuntu 24.04, ubicación en la UE (Alemania o
   Finlandia), añade tu clave pública SSH.
3. Si el proveedor tiene cortafuegos propio, permite solo los puertos **22**
   (SSH), **80** y **443** (HTTP/HTTPS).
4. Anota la IP pública del servidor.

## 2. Dominio

En el panel de tu registrador crea un registro **A** del dominio (o de un
subdominio como `fitness.tudominio.com`) que apunte a la IP del servidor.
Si el servidor tiene IPv6, añade también un registro **AAAA**. La propagación
puede tardar desde unos minutos hasta unas horas; Caddy no podrá obtener el
certificado hasta que el dominio apunte al servidor.

## 3. Base de datos en Supabase

1. En [supabase.com](https://supabase.com) crea un proyecto. Elige una región de
   la UE (la misma o la más cercana a tu servidor) y una **contraseña de base de
   datos** larga: guárdala en tu gestor de contraseñas.
2. Pulsa **Connect** y copia la cadena de conexión. Elige según dónde corra la app:
   - **Session pooler** (puerto 5432, `aws-0-REGIÓN.pooler.supabase.com`): funciona
     por IPv4. Es la opción recomendada si tu VPS no tiene IPv6.
   - **Conexión directa** (`db.PROYECTO.supabase.co:5432`): solo IPv6 salvo que
     contrates el complemento IPv4 de Supabase. Úsala si tu servidor tiene IPv6.
   - El **Transaction pooler** (puerto 6543) también funciona (la aplicación
     desactiva las sentencias preparadas), pero no hace falta con un servidor fijo.
3. Sustituye `[PASSWORD]` por tu contraseña (si tiene `@`, `/`, `:` o `#`,
   codifícalos: `%40`, `%2F`, `%3A`, `%23`). Esa URL es
   `FITNESS_TRACKER_DATABASE_URL`.
4. No hace falta crear tablas: la aplicación las crea sola al arrancar (migraciones
   versionadas en `schema_migrations`) y activa la seguridad por filas (RLS) en todas,
   de modo que la API REST pública de Supabase no puede leer ningún dato. **No uses
   la clave `anon` ni `service_role` en la aplicación**: solo la cadena de conexión.
5. En el panel, *Authentication → Providers*, no actives nada: no se usa.

## 3b. Preparar el servidor

Conéctate como `root` y crea un usuario normal:

```bash
ssh root@IP_DEL_SERVIDOR

adduser deploy
usermod -aG sudo deploy
mkdir -p /home/deploy/.ssh
cp /root/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
```

Abre **otra** terminal y comprueba que entras con `ssh deploy@IP_DEL_SERVIDOR`
antes de seguir. Después, desde esa sesión:

```bash
# Solo claves SSH, sin contraseñas ni acceso directo de root
sudo sed -i 's/^#\?PasswordAuthentication .*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/^#\?PermitRootLogin .*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart ssh

# Cortafuegos
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443
sudo ufw enable

# Actualizaciones de seguridad automáticas
sudo apt update && sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

> Docker publica sus puertos saltándose `ufw`. Por eso `docker-compose.yml` solo
> publica Caddy (80 y 443) y la aplicación no expone ningún puerto al exterior.

Instala Docker:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker deploy
exit        # y vuelve a entrar para que se aplique el grupo
```

## 4. Instalar la aplicación

```bash
sudo mkdir -p /opt/fitnesstracker
sudo chown deploy:deploy /opt/fitnesstracker
git clone https://github.com/pablomontoro5/fitnesstracker.git /opt/fitnesstracker
cd /opt/fitnesstracker

cp .env.example .env
nano .env
```

En `.env` rellena:

- `DOMAIN`: tu dominio, igual que en el registro DNS.
- `FITNESS_TRACKER_JWT_SECRET`: genera uno con
  `python3 -c "import secrets; print(secrets.token_hex(32))"`.
  **Guárdalo en tu gestor de contraseñas.** Si lo cambias, todas las sesiones se cierran.
- `FITNESS_TRACKER_DATABASE_URL`: la cadena de conexión de Supabase del paso 3.
- Deja `FITNESS_TRACKER_REGISTRATION_MODE=invite`.

```bash
chmod 600 .env
docker compose up -d --build
docker compose ps                 # app debe estar «healthy» (si no, ver la URL de la base de datos)
docker compose logs -f caddy      # busca que el certificado se ha obtenido
```

Abre `https://tu-dominio`. Si no carga, mira la sección *Problemas frecuentes*.

## 5. Crear tu cuenta

```bash
docker compose exec app python -m app.cli create-invite
```

Copia el código, entra en la web, pulsa «Crear cuenta» y regístrate.

Para cada persona nueva, genera otro código y envíaselo por un canal privado.
Cada código sirve una vez y caduca a los 7 días.

## 6. Copias de seguridad nocturnas cifradas

La copia es un volcado de PostgreSQL (`pg_dump`) que se cifra con una clave
pública (`age`) y se sube a un almacenamiento externo. Nunca queda una copia sin
cifrar en el servidor. Se conservan los últimos 14 días de copias (configurable con `RETENTION_DAYS`).

### 6.1. En tu ordenador: crear la clave de cifrado

Instala [age](https://github.com/FiloSottile/age) y genera el par de claves:

```bash
age-keygen -o fitness-backup-key.txt
```

Muestra la clave **pública** (empieza por `age1...`). Esa es la que irá al servidor.
La **privada** es el archivo `fitness-backup-key.txt`: guárdalo en tu gestor de
contraseñas y en una segunda copia (por ejemplo, un USB). **Sin esa clave no se
puede restaurar ninguna copia, y no se puede recuperar si la pierdes.**
No la subas al servidor.

### 6.2. Crear el almacenamiento

Crea un *bucket* **privado** en tu proveedor S3 (por ejemplo Backblaze B2) y una
clave de aplicación limitada a ese bucket (lectura y escritura). Apunta el
identificador y la clave.

### 6.3. En el servidor

```bash
sudo apt install -y age rclone
rclone config          # crea un remoto, p. ej. "b2", con la clave del paso anterior
rclone lsd b2:         # comprueba que ve el bucket

sudo mkdir -p /etc/fitness-tracker
sudo nano /etc/fitness-tracker/backup.env
sudo chmod 600 /etc/fitness-tracker/backup.env
```

Contenido de `backup.env`:

```bash
# Para pg_dump usa la conexión directa (o el Session pooler si no hay IPv6),
# nunca el Transaction pooler.
BACKUP_DATABASE_URL=postgresql://postgres.PROYECTO:[PASSWORD]@aws-0-REGION.pooler.supabase.com:5432/postgres
AGE_RECIPIENT=age1...                  # la clave PÚBLICA
RCLONE_REMOTE=b2:nombre-del-bucket/fitness
RETENTION_DAYS=14
# Opcional: un aviso de «latido» (p. ej. healthchecks.io) para enterarte si dejan de hacerse copias
# HEALTHCHECK_URL=https://hc-ping.com/...
```

Prueba una copia a mano y mira que aparece en el bucket:

```bash
sudo /opt/fitnesstracker/deploy/backup.sh
```

> `rclone config` guarda sus credenciales para el usuario que lo ejecuta. Como el
> script se ejecuta con `sudo`/systemd (root), ejecuta `sudo rclone config` y
> usa el mismo usuario en las pruebas.

Activa el temporizador (cada noche sobre las 03:30):

```bash
sudo cp /opt/fitnesstracker/deploy/systemd/fitness-backup.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fitness-backup.timer
systemctl list-timers fitness-backup.timer
```

Para ver el resultado de la última ejecución: `journalctl -u fitness-backup.service -n 30`.

### 6.4. Comprobar que se puede restaurar

En **tu ordenador** (tienes la clave privada), con `rclone` configurado:

```bash
export RCLONE_REMOTE=b2:nombre-del-bucket/fitness
deploy/verify-backup.sh fitness-backup-key.txt
```

Descarga la última copia, la descifra y comprueba con `pg_restore --list` que es
un volcado válido con las tablas de la aplicación (necesita Docker en tu
ordenador). Hazlo la primera vez y después una vez al mes. Una vez, además, haz una
restauración completa de prueba (sección 8) en una base vacía.

## 7. Operación diaria

| Tarea | Comando (en `/opt/fitnesstracker`) |
| --- | --- |
| Ver registros | `docker compose logs -f app` |
| Reiniciar | `docker compose restart app` |
| Nuevo código de invitación | `docker compose exec app python -m app.cli create-invite` |
| Código de recuperación de contraseña | `docker compose exec app python -m app.cli create-reset-code --email persona@ejemplo.com` |
| Copia manual | `sudo deploy/backup.sh` |
| Estado | `docker compose ps` |

**Actualizar a una versión nueva:**

```bash
cd /opt/fitnesstracker
git pull
docker compose up -d --build
docker compose logs --tail 50 app
```

Los datos están en Supabase y no se tocan al reconstruir. Si una versión nueva
incluye una migración, se aplica sola al arrancar. Haz una copia manual
(`sudo deploy/backup.sh`) antes de actualizar si el cambio toca la base de datos.

## 8. Restaurar una copia

Restaurar sustituye los datos de **todas** las cuentas por los de la copia, así que
es una operación de emergencia. Se hace desde tu ordenador (con Docker):

1. Descarga la copia y descífrala:
   ```bash
   rclone copyto b2:nombre-del-bucket/fitness/fitness_tracker_FECHA.dump.age copia.dump.age
   age -d -i fitness-backup-key.txt -o copia.dump copia.dump.age
   ```
2. Para el contenedor `app` en el servidor (`docker compose stop app`) para que
   nadie escriba mientras restauras.
3. Restaura en la base de Supabase (misma URL que `BACKUP_DATABASE_URL`).
   `--clean --if-exists` borra y recrea las tablas de la copia:
   ```bash
   docker run --rm -v "$PWD:/b:ro" postgres:17-alpine \
     pg_restore --dbname="postgresql://postgres.PROYECTO:[PASSWORD]@aws-0-REGION.pooler.supabase.com:5432/postgres" \
     --clean --if-exists --no-owner --no-privileges /b/copia.dump
   ```
4. Arranca de nuevo la app (`docker compose start app`): comprobará que el
   esquema está al día y que la seguridad por filas sigue activada.

**Si has perdido el servidor de la app:** los datos siguen en Supabase. Repite los
pasos 1 a 4 en un servidor nuevo con el mismo `FITNESS_TRACKER_DATABASE_URL` y el mismo
`FITNESS_TRACKER_JWT_SECRET` (así no se cierran las sesiones). **Si has perdido la
base de datos**, crea un proyecto nuevo, cambia la URL y restaura la última copia.

### Restaurar los datos de una sola persona

Si solo hace falta recuperar a un usuario (borró algo por error), no restaures
la base entera: esa persona sube su exportación JSON en **Mi cuenta → Restaurar
desde una exportación**. Solo se sustituyen sus datos y nadie más se ve afectado.
Una persona que no conserve su exportación no puede usar este método; para ella
tendrías que restaurar la copia en una base aparte y extraer sus datos de ahí.

## 9. Lista de comprobación de seguridad

- [ ] `.env` con permisos `600`, fuera de Git y con un secreto aleatorio de 64 caracteres.
- [ ] `FITNESS_TRACKER_REGISTRATION_MODE=invite`.
- [ ] Acceso SSH solo con clave, sin `root`, `ufw` activo.
- [ ] La clave privada de `age` guardada en dos sitios y **no** en el servidor.
- [ ] La contraseña de la base de datos de Supabase en tu gestor de contraseñas, y ninguna clave `anon`/`service_role` en la app.
- [ ] Una copia restaurada y verificada (`verify-backup.sh`).
- [ ] Alerta de «latido» configurada para saber si las copias se paran.

## 10. Limitaciones conocidas

- Un solo servidor y un solo proceso (el limitador de intentos está en memoria).
  Si el servidor se cae, la web no está disponible hasta reiniciarlo.
- La recuperación de contraseña no usa correo: la persona te pide un código y tú
  lo generas con el comando de la tabla anterior (válido 60 minutos, un solo uso).
  Entrégalo por un canal privado y comprueba que quien lo pide es quien dice ser.
- La documentación interactiva (`/docs`, `/redoc`) está desactivada por defecto.
  No pongas `FITNESS_TRACKER_ENABLE_DOCS` en producción.
- No hay CORS a propósito: el frontend se sirve desde el mismo dominio que la
  API, así que el navegador bloquea las peticiones desde cualquier otra web. No
  añadas `CORSMiddleware` salvo que un frontend en otro dominio lo necesite, y
  en ese caso con su origen exacto, nunca `*`.
- La única dependencia externa del navegador es Chart.js (página de
  estadísticas), con versión fija y hash de integridad (SRI): si el CDN sirve
  otro archivo, el navegador lo rechaza.
- Los registros (inicios de sesión, fallos, cambios de contraseña, borrados,
  cambios de datos de la cuenta) salen por la salida estándar: `docker compose logs -f app`.
  No incluyen emails, contraseñas, tokens ni códigos; las cuentas aparecen por id.
- Restaurar una copia completa sustituye los datos de **todas** las cuentas y
  hace reaparecer las cuentas que se borraron después de ella: si hubo
  solicitudes de borrado, vuelve a aplicarlas.
- El plan gratuito de Supabase pausa los proyectos inactivos y tiene límites de
  tamaño y de conexiones; la app usa un máximo de conexiones pequeño
  (`FITNESS_TRACKER_DB_POOL_MAX`, 10 por defecto). Con usuarios reales, valora el
  plan de pago.
- **Datos personales:** la app guarda datos de salud y actividad. Con usuarios
  reales, informa de qué datos guardas, para qué y cómo pueden pedir su borrado
  (RGPD). Esto no es asesoramiento legal. Cada usuario puede borrar su cuenta
  desde «Mi cuenta»; los datos borrados siguen en las copias de seguridad cifradas
  hasta que caducan (`RETENTION_DAYS`, 14 días por defecto).

## Problemas frecuentes

- **El navegador dice que el sitio no es seguro / no hay certificado:** el dominio
  no apunta aún al servidor, o los puertos 80/443 están cerrados. Comprueba el DNS
  (`dig +short tu-dominio`) y `docker compose logs caddy`.
- **`app` no llega a «healthy»:** mira `docker compose logs app`. Lo más habitual es
  un `FITNESS_TRACKER_JWT_SECRET` ausente o de menos de 32 bytes, o una
  `FITNESS_TRACKER_DATABASE_URL` incorrecta: contraseña mal codificada, o conexión
  directa desde un servidor sin IPv6 (usa el Session pooler).
- **Primera petición muy lenta tras días sin uso:** el proyecto gratuito de
  Supabase estaba pausado; reactívalo desde su panel.
- **«Se necesita un código de invitación válido»:** el código ya se usó, caducó o
  se copió incompleto (comprueba la primera letra).
- **Muchos «429 Demasiados intentos» para todos los usuarios:** el limitador está
  viendo la IP del proxy en lugar de la del cliente. Con este compose no debería
  pasar; si cambias el despliegue, arranca uvicorn con `--proxy-headers`.
- **La copia nocturna falla:** `journalctl -u fitness-backup.service -n 50`. Un fallo
  de `rclone` suele ser una credencial caducada o un nombre de bucket mal escrito.
