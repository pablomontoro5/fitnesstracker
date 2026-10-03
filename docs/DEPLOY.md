# Despliegue en un servidor (VPS + Docker + Caddy)

Guía paso a paso para publicar la aplicación con HTTPS, usuarios reales y copias
de seguridad cifradas fuera del servidor. Pensada para pocos usuarios (unos 5 al
empezar) con SQLite en un único servidor.

```
Internet ──443──▶ Caddy (HTTPS automático) ──▶ FastAPI (contenedor "app")
                                                   │
                                          volumen Docker: base de datos SQLite
                                                   │
                      copia nocturna ──▶ age (cifrado) ──▶ rclone ──▶ almacenamiento externo (S3/B2)
```

## 0. Qué necesitas

| Cosa | Para qué | Coste orientativo |
| --- | --- | --- |
| Un VPS en la UE (p. ej. Hetzner Cloud, plan más pequeño, Ubuntu 24.04) | Ejecutar la app | Unos pocos euros al mes. **Comprueba el precio actual**: Hetzner subió tarifas en 2026 |
| Un dominio | HTTPS con certificado propio | ≈10 €/año |
| Una cuenta de almacenamiento S3 compatible (p. ej. Backblaze B2) | Guardar las copias fuera del servidor | Céntimos al mes con una base de datos pequeña |

Contratar el servidor, comprar el dominio y crear la cuenta de almacenamiento (pasos 1, 2 y 6.2) solo puedes hacerlo tú.

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

## 3. Preparar el servidor

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
- `FITNESS_TRACKER_ADMIN_EMAILS`: tu email.
- Deja `FITNESS_TRACKER_REGISTRATION_MODE=invite`.

```bash
chmod 600 .env
docker compose up -d --build
docker compose ps                 # app debe estar «healthy»
docker compose logs -f caddy      # busca que el certificado se ha obtenido
```

Abre `https://tu-dominio`. Si no carga, mira la sección *Problemas frecuentes*.

## 5. Crear tu cuenta de administrador

```bash
docker compose exec app python -m app.cli create-invite
```

Copia el código, entra en la web, pulsa «Crear cuenta» y regístrate con el email
que pusiste en `FITNESS_TRACKER_ADMIN_EMAILS`. Esa cuenta podrá usar Backups y
Restauración.

Para cada persona nueva, genera otro código y envíaselo por un canal privado.
Cada código sirve una vez y caduca a los 7 días.

## 6. Copias de seguridad nocturnas cifradas

La copia se genera dentro del contenedor, se verifica, se cifra con una clave
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
COMPOSE_DIR=/opt/fitnesstracker
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

Descarga la última copia, la descifra y comprueba su integridad. Hazlo la primera
vez y después una vez al mes.

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

Los datos están en un volumen de Docker y no se tocan al reconstruir. Haz una
copia manual (`sudo deploy/backup.sh`) antes de actualizar si el cambio toca la base de datos.

## 8. Restaurar una copia

1. Descarga la copia de tu almacenamiento y descífrala **en tu ordenador**:
   ```bash
   rclone copyto b2:nombre-del-bucket/fitness/fitness_tracker_FECHA.db.age copia.db.age
   age -d -i fitness-backup-key.txt -o copia.db copia.db.age
   ```
2. Entra en la web como administrador, abre **Backups** y sube `copia.db` en
   «Restaurar». La app guarda antes una copia de seguridad del estado actual.

**Si has perdido el servidor entero:** repite los pasos 1 a 5 en un servidor nuevo
(usa el mismo `FITNESS_TRACKER_JWT_SECRET` si lo tienes, para que no se cierren las
sesiones), regístrate como administrador con una invitación nueva y restaura la copia
como en el punto anterior. Las cuentas y datos vuelven con ella.

## 9. Lista de comprobación de seguridad

- [ ] `.env` con permisos `600`, fuera de Git y con un secreto aleatorio de 64 caracteres.
- [ ] `FITNESS_TRACKER_REGISTRATION_MODE=invite`.
- [ ] Acceso SSH solo con clave, sin `root`, `ufw` activo.
- [ ] La clave privada de `age` guardada en dos sitios y **no** en el servidor.
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
- Los registros (inicios de sesión, fallos, cambios de contraseña, borrados,
  copias y restauraciones) salen por la salida estándar: `docker compose logs -f app`.
  No incluyen emails, contraseñas, tokens ni códigos; las cuentas aparecen por id.
- La restauración sustituye la base de datos **completa** (todas las cuentas).
  Al restaurar una copia reaparecen las cuentas que se borraron después de ella:
  si hubo solicitudes de borrado, vuelve a aplicarlas.
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
  un `FITNESS_TRACKER_JWT_SECRET` ausente o de menos de 32 bytes.
- **«Se necesita un código de invitación válido»:** el código ya se usó, caducó o
  se copió incompleto (comprueba la primera letra).
- **Muchos «429 Demasiados intentos» para todos los usuarios:** el limitador está
  viendo la IP del proxy en lugar de la del cliente. Con este compose no debería
  pasar; si cambias el despliegue, arranca uvicorn con `--proxy-headers`.
- **La copia nocturna falla:** `journalctl -u fitness-backup.service -n 50`. Un fallo
  de `rclone` suele ser una credencial caducada o un nombre de bucket mal escrito.
