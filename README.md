# Fitness Tracker — Health & Training Log 🏋️‍♂️🏃‍♂️

**Fitness Tracker** es una aplicación web personal para centralizar el seguimiento diario de actividad, entrenamientos de gimnasio, running, alimentación, composición corporal y objetivos de actividad.

El proyecto sigue una arquitectura incremental: backend modular con FastAPI, persistencia local con SQLite, API documentada automáticamente, pruebas con Pytest y un frontend responsive en HTML, CSS y JavaScript. La aplicación admite varias cuentas con datos aislados por usuario y registro por invitación, y está pensada para desplegarse en un servidor propio. Más adelante podrá evolucionar a PWA o a un cliente móvil conectado a la misma API.

---

## Objetivo

Registrar en un único lugar datos que normalmente quedan repartidos entre notas, hojas de cálculo y varias aplicaciones:

- Pasos diarios y actividad general.
- Rutinas de gimnasio por sesión, ejercicio, serie, repeticiones, carga y RIR.
- Plantillas de entrenamiento reutilizables.
- Seguimiento de progreso por ejercicio, volumen y notas técnicas.
- Sesiones de running con distancia, duración y ritmo medio por kilómetro.
- Comidas, alimentos, calorías y macronutrientes diarios.
- Peso, altura, IMC y evolución corporal.
- Objetivos de pasos diarios, entrenamientos semanales y kilómetros de running semanales.
- Exportación JSON y copias de seguridad/restauración de la base SQLite.

---

## Funcionalidades actuales

### Pasos diarios

- Crear, consultar, editar y eliminar registros diarios.
- Guardar pasos y notas por fecha.
- Evitar registros duplicados para un mismo día.

### Entrenamiento

- Crear, consultar, editar y eliminar sesiones de gimnasio.
- Añadir ejercicios ordenados por posición dentro de una sesión.
- Registrar grupo muscular, notas técnicas y ejercicios personalizados.
- Añadir, editar y eliminar series con:
  - Tipo de serie: `warmup`, `approximation`, `working` o `drop_set`.
  - Rango objetivo de repeticiones.
  - Repeticiones realizadas.
  - Carga en kilogramos.
  - RIR y observaciones.
- Calcular volumen por serie y progreso básico por ejercicio.
- Repetir una sesión existente para crear una nueva sesión con la fecha actual.

### Plantillas de entrenamiento

- Crear, listar, consultar y eliminar plantillas.
- Configurar ejercicios y series previstas por plantilla.
- Mantener orden de ejercicios y series mediante posiciones únicas.
- Crear una sesión real desde una plantilla sin modificar la plantilla original.
- Gestionar plantillas y utilizarlas desde la interfaz de entrenamiento.

### Running

- Crear, consultar, editar y eliminar sesiones de running.
- Guardar fecha, distancia, duración, ritmo medio y notas.
- Calcular automáticamente el ritmo medio en segundos por kilómetro.

### Nutrición

- Crear días de nutrición.
- Añadir comidas ordenadas dentro de un día.
- Añadir alimentos con cantidad, calorías y macronutrientes.
- Consultar la información nutricional diaria.

### Métricas corporales

- Registrar peso, altura y notas por fecha.
- Calcular el IMC automáticamente.
- Consultar métricas corporales y su evolución desde el módulo de estadísticas.

### Estadísticas

- Consultar un resumen de pasos, entrenamiento, running y métricas corporales por periodo.
- Visualizar series temporales de pasos, peso y kilómetros de running.

### Objetivos

- Configurar un objetivo de pasos diarios.
- Configurar un objetivo semanal de sesiones de entrenamiento.
- Configurar un objetivo semanal de kilómetros de running.
- Calcular el progreso en el backend a partir de los registros existentes.
- Mostrar valor actual, objetivo, porcentaje de progreso y estado de completado.
- Eliminar objetivos sin eliminar los registros de actividad asociados.

### Datos y copias de seguridad

- Exportar a JSON los datos de la cuenta autenticada (cada usuario solo recibe los suyos).
- Descargar una copia completa de la base SQLite (solo administradores).
- Restaurar una copia SQLite desde la interfaz (solo administradores).
- Validar integridad SQLite, tablas necesarias y columnas obligatorias antes de restaurar.
- Crear automáticamente un backup de seguridad antes de reemplazar los datos activos.

---

## Decisiones de producto

- **Web primero y móvil después:** el frontend es responsive desde el inicio; una PWA podrá permitir su instalación en móvil más adelante.
- **Datos propios y editables:** los registros creados por el usuario se pueden consultar, corregir y eliminar.
- **Registro rápido:** los campos esenciales son obligatorios; notas y datos adicionales son opcionales.
- **Fuente de verdad en el backend:** los cálculos de ritmo, IMC, volumen y progreso de objetivos se realizan en la API.
- **Sin afirmaciones médicas:** peso e IMC son métricas de seguimiento, no diagnósticos ni recomendaciones sanitarias.
- **Seguridad de datos local:** las restauraciones validan el archivo y generan una copia de protección antes de modificar la base activa.

---

## Tecnologías

### Backend

- Python
- FastAPI
- SQLite mediante `sqlite3`
- Pydantic para validación de datos
- `python-multipart` para subida de copias SQLite
- Pytest y HTTPX para pruebas

### Frontend

- HTML
- CSS
- JavaScript sin framework
- Diseño responsive orientado a móvil

### Evolución prevista

- Importación GPX y mapas de recorrido con Leaflet + OpenStreetMap.
- PWA mediante manifest y service worker.
- Modo sin conexión básico.
- Objetivos de nutrición y composición corporal.
- PostgreSQL si se requiere despliegue multiusuario o mayor concurrencia.

FastAPI ofrece documentación interactiva en `/docs` y documentación alternativa en `/redoc`.

---

## Rutas del frontend

Con la aplicación en ejecución, las vistas principales están disponibles en:

| Ruta | Descripción |
| --- | --- |
| `/` | Panel principal de navegación |
| `/static/workouts/` | Sesiones, ejercicios, series, plantillas y progreso de entrenamiento |
| `/static/daily-steps/` | Registro y edición de pasos diarios |
| `/static/runs/` | Registro e historial de running |
| `/static/nutrition/` | Registro de días, comidas y alimentos |
| `/static/statistics/` | Resúmenes y gráficas por periodo |
| `/static/goals/` | Configuración y seguimiento de objetivos de actividad |
| `/static/login/` | Inicio de sesión y registro (con código de invitación) |
| `/static/backups/` | Descarga y restauración de copias SQLite (solo administradores) |
| `/docs` | Documentación interactiva de la API |
| `/redoc` | Documentación alternativa de la API |

Los archivos estáticos se sirven mediante FastAPI con `StaticFiles(..., html=True)`, por lo que cada módulo puede disponer de su propio `index.html` y JavaScript.

---

## Estructura del proyecto

```text
fitness-tracker/
├── app/
│   ├── main.py
│   ├── db.py
│   ├── schemas.py
│   ├── routers/
│   │   ├── backups.py
│   │   ├── body_metrics.py
│   │   ├── daily_logs.py
│   │   ├── exports.py
│   │   ├── goals.py
│   │   ├── nutrition_days.py
│   │   ├── nutrition_foods.py
│   │   ├── nutrition_meals.py
│   │   ├── restores.py
│   │   ├── runs.py
│   │   ├── statistics.py
│   │   ├── workout_exercises.py
│   │   ├── workout_progress.py
│   │   ├── workout_sessions.py
│   │   ├── workout_sets.py
│   │   └── workout_templates.py
│   ├── services/
│   │   ├── backups.py
│   │   ├── exports.py
│   │   └── restores.py
│   └── frontend/
│       ├── index.html                 # Panel principal
│       ├── home.js                    # Verificación de sesión, logout y exportación JSON
│       ├── auth.js                    # Token, apiFetch y logout compartidos
│       ├── list-states.js             # Estados de carga y error con «Reintentar»
│       ├── style.css                  # Estilos compartidos
│       ├── backups/
│       │   ├── index.html
│       │   └── backups.js
│       ├── daily-steps/
│       │   ├── index.html
│       │   └── daily-steps.js
│       ├── goals/
│       │   ├── index.html
│       │   └── goals.js
│       ├── nutrition/
│       │   ├── index.html
│       │   └── nutrition.js
│       ├── runs/
│       │   ├── index.html
│       │   └── runs.js
│       ├── statistics/
│       │   ├── index.html
│       │   └── statistics.js
│       ├── workout-templates/
│       │   ├── index.html
│       │   └── workout_templates.js
│       └── workouts/
│           ├── index.html
│           ├── workouts.js
│           ├── history.html
│           └── history.js
├── data/                              # Datos locales; no versionar bases ni backups
├── tests/
│   ├── conftest.py
│   ├── test_backups.py
│   ├── test_backups_router.py
│   ├── test_body_metrics.py
│   ├── test_daily_logs.py
│   ├── test_exports.py
│   ├── test_exports_router.py
│   ├── test_goals.py
│   ├── test_restores.py
│   ├── test_restores_router.py
│   ├── test_runs.py
│   ├── test_statistics.py
│   ├── test_workout_templates.py
│   └── ...
├── requirements.txt
└── README.md
```

Los routers separan los endpoints por dominio. El frontend se organiza por funcionalidad: cada módulo posee su propia vista HTML y lógica JavaScript, mientras `style.css` concentra la apariencia común.

---

## Catálogo de ejercicios sugeridos

El módulo de entrenamiento incluye un catálogo inicial de ejercicios agrupados por músculo. Al seleccionar un grupo muscular se muestran sugerencias y, al elegir una, se completan automáticamente los campos de nombre y grupo muscular.

Las sugerencias son opcionales: los campos se mantienen editables para poder registrar variantes, máquinas concretas o ejercicios personalizados. El catálogo se mantiene inicialmente en `app/frontend/workouts/workouts.js` y podrá trasladarse al backend en una iteración futura.

---

## Modelo de datos

| Entidad | Campos principales |
| --- | --- |
| `daily_logs` | `id`, `date`, `steps`, `notes`, `created_at` |
| `body_metrics` | `id`, `date`, `weight_kg`, `height_cm`, `bmi`, `notes`, `created_at` |
| `workout_sessions` | `id`, `date`, `name`, `notes`, `created_at` |
| `workout_exercises` | `id`, `workout_session_id`, `name`, `muscle_group`, `position`, `technique_notes`, `created_at` |
| `workout_sets` | `id`, `workout_exercise_id`, `set_type`, `position`, `target_rep_range`, `repetitions`, `weight_kg`, `rir`, `notes`, `created_at` |
| `runs` | `id`, `date`, `distance_km`, `duration_seconds`, `average_pace_seconds_km`, `notes`, `created_at` |
| `nutrition_days` | `id`, `date`, `notes`, `created_at` |
| `nutrition_meals` | `id`, `nutrition_day_id`, `name`, `position`, `created_at` |
| `nutrition_foods` | `id`, `nutrition_meal_id`, `name`, `quantity_g`, `calories`, `protein_g`, `carbs_g`, `fat_g`, `position`, `notes`, `created_at` |
| `workout_templates` | `id`, `name`, `notes`, `created_at` |
| `workout_template_exercises` | `id`, `workout_template_id`, `name`, `muscle_group`, `position`, `technique_notes`, `created_at` |
| `workout_template_sets` | `id`, `workout_template_exercise_id`, `set_type`, `position`, `target_rep_range`, `repetitions`, `weight_kg`, `rir`, `notes`, `created_at` |
| `fitness_goals` | `id`, `goal_type`, `target_value`, `created_at`, `updated_at` |
| `users` | `id`, `email`, `display_name`, `password_hash`, `is_active`, `created_at` |
| `invitations` | `id`, `code_hash`, `created_at`, `expires_at`, `used_at`, `used_by_user_id` |

### Convenciones importantes

- Las entidades de datos incluyen `user_id` (las tablas hijas se aíslan a través de su padre); las columnas de la tabla anterior son las principales, no todas.
- `weight_kg`, `height_cm`, `distance_km` y las cargas de gimnasio son valores numéricos.
- `duration_seconds` y `average_pace_seconds_km` permiten cálculos y ordenación fiables de las carreras.
- `rir` representa *reps in reserve* y puede ser decimal o nulo.
- `set_type` diferencia `warmup`, `approximation`, `working` y `drop_set`.
- Las posiciones de ejercicios y series son únicas dentro de su entidad padre.
- `fitness_goals.goal_type` acepta `daily_steps`, `weekly_workouts` o `weekly_running_km`.

---

## Cálculos

- **IMC:** `peso_kg / (altura_cm / 100)²`.
- **Ritmo medio:** `duración total en segundos / distancia en km`.
- **Volumen de una serie:** `repeticiones × carga_kg`.
- **Volumen de un ejercicio o sesión:** suma de los volúmenes de sus series de trabajo.
- **Objetivo diario de pasos:** pasos del registro correspondiente a hoy.
- **Objetivo semanal de entrenamientos:** sesiones registradas desde el lunes hasta hoy.
- **Objetivo semanal de running:** suma de kilómetros de las carreras registradas desde el lunes hasta hoy.

Ejemplo: una serie de 10 repeticiones con 50 kg aporta 500 kg de volumen. Un objetivo de 8 km semanales mostrará el valor real acumulado, aunque la barra visual se limita al 100 % al completarlo o superarlo.

---

## Endpoints principales

| Método | Endpoint | Propósito |
| --- | --- | --- |
| `POST` | `/auth/register`, `/auth/login` | Crear cuenta (con invitación) e iniciar sesión |
| `GET` | `/auth/me` | Datos de la cuenta autenticada |
| `GET` / `POST` | `/daily-logs/` | Consultar o crear registros de pasos |
| `GET` / `PUT` / `DELETE` | `/daily-logs/{log_date}` | Consultar, editar o borrar un registro diario |
| `GET` / `POST` | `/body-metrics/` | Consultar o registrar peso, altura e IMC |
| `GET` / `POST` | `/workout-sessions/` | Listar o crear sesiones de gimnasio |
| `GET` / `PUT` / `DELETE` | `/workout-sessions/{session_id}` | Consultar, editar o eliminar una sesión |
| `POST` | `/workout-sessions/{session_id}/repeat` | Repetir una sesión con la fecha actual |
| `POST` / `GET` | `/workout-sessions/{session_id}/exercises/` | Crear o listar ejercicios de una sesión |
| `GET` / `PUT` / `DELETE` | `/workout-exercises/{exercise_id}` | Consultar, editar o eliminar un ejercicio |
| `POST` / `GET` | `/workout-exercises/{exercise_id}/sets/` | Crear o listar series de un ejercicio |
| `GET` / `PUT` / `DELETE` | `/workout-sets/{set_id}` | Consultar, editar o eliminar una serie |
| `GET` | `/workouts/progress?exercise_name={name}` | Consultar progreso por ejercicio |
| `GET` / `POST` | `/runs/` | Listar o crear carreras |
| `GET` / `PUT` / `DELETE` | `/runs/{run_id}` | Consultar, editar o eliminar una carrera |
| `GET` / `POST` | `/nutrition-days/` | Gestionar días de nutrición |
| `GET` / `POST` | `/workout-templates/` | Listar o crear plantillas de entrenamiento |
| `GET` / `DELETE` | `/workout-templates/{template_id}` | Consultar o eliminar una plantilla |
| `POST` | `/workout-templates/{template_id}/create-session` | Crear una sesión real desde una plantilla |
| `PUT` | `/goals/{goal_type}` | Crear o actualizar un objetivo |
| `GET` | `/goals/` | Listar objetivos configurados |
| `GET` | `/goals/progress` | Consultar progreso de objetivos |
| `DELETE` | `/goals/{goal_type}` | Eliminar un objetivo |
| `*` | `/recovery-logs`, `/calendar`, `/planned-workouts`, `/food-library`, `/meal-templates`, `/exercise-catalog` | Recuperación, calendario, planificación, biblioteca de alimentos, plantillas de comida y catálogo de ejercicios |
| `GET` | `/exports/fitness-tracker.json` | Descargar en JSON los datos de la cuenta autenticada |
| `POST` | `/backups/database` | Descargar una copia SQLite completa (administrador) |
| `POST` | `/restores/database` | Restaurar una copia SQLite validada (administrador) |

Consulta `/docs` para ver el catálogo completo, parámetros, modelos y respuestas de la API.

---

## Roadmap

### Fase 1 — Base funcional

- [x] Crear proyecto FastAPI, SQLite e inicialización de tablas.
- [x] Añadir registro diario de pasos.
- [x] Crear, consultar, editar y eliminar sesiones de gimnasio.
- [x] Añadir ejercicios y series ordenadas dentro de una sesión.
- [x] Calcular volumen básico por serie y progreso por ejercicio.
- [x] Implementar registro de peso, altura e IMC.
- [x] Crear frontend responsive con páginas modulares.
- [x] Añadir registro de running con distancia, duración y ritmo.
- [x] Añadir registro de nutrición y macronutrientes.
- [x] Añadir estadísticas y gráficas simples.
- [x] Añadir plantillas de entrenamiento reutilizables.
- [x] Añadir exportación JSON, backup SQLite y restauración validada.
- [x] Añadir objetivos de pasos, entrenamientos y running.

### Fase 2 — Seguimiento avanzado

- [x] Añadir resumen de actividad y gráficas temporales de pasos, peso y
  kilómetros de running por periodo.
- [x] Añadir progreso por ejercicio basado en series de trabajo.
- [x] Detectar marcas personales de carga, repeticiones, volumen por serie,
  volumen por sesión y 1RM estimado.
- [x] Añadir objetivos diarios de calorías, proteína, carbohidratos y grasa.
- [x] Añadir objetivos diarios de sueño y objetivos semanales de descanso.
- [x] Añadir consistencia, días de objetivo cumplido, racha actual y mejor
  racha para pasos y sueño.
- [x] Añadir seguimiento de composición corporal: porcentaje graso, masa
  grasa, masa magra y perímetros.
- [x] Añadir objetivos de peso, porcentaje graso, perímetros y composición
  corporal.
- [x] Añadir medias móviles y comparativas entre periodos.
- [x] Ampliar gráficas de IMC, composición corporal, volumen de entrenamiento
  y ritmo de running.
- [x] API de calendario de actividad y planificación de sesiones.
- [ ] Interfaz del calendario y la planificación de sesiones.
- [x] Ampliar el catálogo de ejercicios con equipamiento, variantes, músculos
  principales/secundarios e indicaciones técnicas.
- [x] API de biblioteca de alimentos, comidas frecuentes y plantillas de comida.
- [ ] Interfaz de la biblioteca de alimentos y las plantillas de comida.
- [x] Mejorar filtros, estados vacíos, carga y mensajes de error entre
  frontend y backend.

### Fase 3 — Privacidad completa y despliegue

- [x] Registro, login y autenticación mediante tokens.
- [x] Hash seguro de contraseñas.
- [x] Aislamiento por usuario de pasos, recuperación, objetivos,
  entrenamientos, carreras, métricas corporales y estadísticas.
- [x] Añadir `user_id` a nutrición: días, comidas y alimentos.
- [x] Añadir `user_id` a plantillas y a sus ejercicios/series.
- [x] Convertir exportación JSON en una exportación exclusiva de la cuenta
  autenticada.
- [x] Sustituir el backup SQLite completo por exportaciones por usuario o
  backups administrativos protegidos.
- [ ] Diseñar restauración segura por usuario, sin sobrescribir datos de otras
  cuentas.
- [x] Añadir control de sesión en frontend: login, logout, expiración de token
  y envío consistente de `Authorization: Bearer ...`.
- [ ] Añadir recuperación/cambio de contraseña.
- [x] Registro por invitación, límite de intentos y secreto JWT validado.
- [x] SQLite en modo WAL con copias de seguridad portables.
- [ ] Configurar CORS restrictivo, HTTPS (Caddy), logs y CI/CD.
- [ ] Desplegar en un servidor (Docker + Caddy) con copia nocturna fuera del servidor.
- [ ] Migrar a PostgreSQL solo si crece el número de usuarios o la concurrencia.

### Fase 4 — Móvil y experiencia PWA

- [ ] Añadir `manifest.webmanifest`, iconos y configuración de instalación.
- [ ] Añadir service worker y caché de recursos esenciales.
- [ ] Permitir instalar la aplicación desde el navegador en móvil y escritorio compatible.
- [ ] Añadir modo sin conexión básico y sincronización al recuperar conexión.
- [ ] Importar archivos GPX y visualizar rutas de running con Leaflet.

### Fase 5 — Asistente personal con IA

- [ ] Crear un chat personal vinculado a la cuenta autenticada.
- [ ] Permitir consultas sobre objetivos, pasos, entrenamientos, running, nutrición y evolución corporal.
- [ ] Conectar la IA a herramientas internas con datos agregados y filtrados por usuario.
- [ ] Añadir explicaciones de métricas como IMC, RIR, ritmo y volumen.
- [ ] Mostrar límites claros: el asistente no sustituye a profesionales sanitarios, nutricionistas o entrenadores.
- [ ] Pedir confirmación explícita antes de que el asistente cree, modifique o elimine registros.

---

## Puesta en marcha

### 1. Clonar el repositorio

```bash
git clone https://github.com/pablomontoro5/fitnesstracker.git
cd fitnesstracker
```

### 2. Crear un entorno virtual

```bash
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Windows CMD:

```bat
.venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
python -m pip install -r requirements.txt
```

### 4. Ejecutar la aplicación

```bash
python -m uvicorn app.main:app --reload --port 8001
```

### 5. Configurar variables de entorno

| Variable | Obligatoria | Descripción |
| --- | --- | --- |
| `FITNESS_TRACKER_JWT_SECRET` | Sí | Clave para firmar los tokens. **Mínimo 32 bytes**: el servidor no arranca con una más corta. Genera una con `python -c "import secrets; print(secrets.token_hex(32))"`. |
| `FITNESS_TRACKER_ADMIN_EMAILS` | No | Emails de administradores, separados por comas. Solo ellos pueden descargar copias SQLite y restaurarlas. Si no se define, nadie puede. |
| `FITNESS_TRACKER_REGISTRATION_MODE` | No | `invite` (por defecto): para registrarse hace falta un código de invitación. `open`: registro abierto, útil solo en desarrollo local. |

### Registro por invitación

Por defecto nadie puede crear una cuenta sin un código de un solo uso, que se
genera **en el servidor**:

```bash
python -m app.cli create-invite --days 7
```

El código se muestra una sola vez (en la base de datos solo se guarda su hash),
caduca a los 7 días y se pega en el campo «Código de invitación» del registro.
Para crear la primera cuenta de administrador, genera una invitación y regístrate
con el email que pusiste en `FITNESS_TRACKER_ADMIN_EMAILS`. Así nadie puede
adelantarse y quedarse con ese rol.

En desarrollo local puedes saltarte las invitaciones con
`export FITNESS_TRACKER_REGISTRATION_MODE=open`.

### Límite de intentos

- Login: 5 contraseñas incorrectas por cuenta y dirección IP, y 20 por IP, cada
  15 minutos. Después responde `429` con la cabecera `Retry-After`.
- Registro: 10 intentos por IP y hora.
- El contador está en memoria y vale para **un solo proceso** (un único
  `uvicorn`). Si algún día ejecutas varios workers, cada uno llevará su cuenta.
- Detrás de un proxy (Caddy, Nginx) arranca uvicorn con
  `--proxy-headers --forwarded-allow-ips="<IP del proxy>"` para que cuente la IP
  real del cliente y no la del proxy.

### Base de datos

SQLite funciona en modo WAL, así que junto a `data/fitness_tracker.db` verás
los archivos `-wal` y `-shm`; no los borres con la app en marcha. Las copias de
seguridad se generan como un único archivo `.db` portable.

### 6. Abrir la aplicación

- Aplicación: [http://127.0.0.1:8001/](http://127.0.0.1:8001/)
- Swagger UI: [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)
- ReDoc: [http://127.0.0.1:8001/redoc](http://127.0.0.1:8001/redoc)

### 7. Ejecutar pruebas

```bash
python -m pytest -q
```

---

## Limitaciones actuales

- La API dispone de cuentas, autenticación mediante token y aislamiento por usuario
  para pasos, recuperación, objetivos, entrenamientos, carreras, métricas
  corporales y estadísticas.
- La exportación JSON exige sesión y solo incluye los datos de la cuenta; no
  incluye aún recuperación, objetivos, plantillas, calendario ni biblioteca de
  alimentos.
- Las copias SQLite y las restauraciones operan sobre la base de datos completa
  (todas las cuentas y sus hashes de contraseña), por lo que solo pueden usarlas
  administradores. La restauración por usuario sigue pendiente.
- La persistencia es SQLite en un único servidor (adecuado para pocos usuarios);
  no hay sincronización en la nube ni varias réplicas.
- Los pasos, entrenamientos, carreras y datos nutricionales se introducen manualmente.
- No hay integración actual con relojes, Apple Health, Health Connect ni dispositivos de actividad.
- Los mapas, rutas GPS e importación GPX aún no están implementados.
- El registro nutricional no sustituye orientación profesional.
- El IMC es una métrica descriptiva y no evalúa por sí solo salud ni composición corporal.

---

## Autor

Desarrollado por **Pablo Javier Montoro Bermúdez** como proyecto personal de aprendizaje y portfolio full-stack.
