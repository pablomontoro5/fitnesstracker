# Fitness Tracker — Health & Training Log 🏋️‍♂️🏃‍♂️

**Fitness Tracker** es una aplicación web personal para centralizar el seguimiento diario de actividad, entrenamientos de gimnasio, running, alimentación, composición corporal y objetivos de actividad.

El proyecto sigue una arquitectura incremental: backend modular con FastAPI, persistencia local con SQLite, API documentada automáticamente, pruebas con Pytest y un frontend responsive en HTML, CSS y JavaScript. La aplicación está pensada inicialmente para un único usuario y uso local, con posibilidad de evolucionar más adelante a PWA o a un cliente móvil conectado a la misma API.

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

- Exportar los datos de la aplicación a JSON.
- Descargar una copia completa de la base SQLite.
- Restaurar una copia SQLite desde la interfaz.
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
| `/static/backups/` | Descarga y restauración de copias SQLite |
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
│       ├── home.js                    # Exportación JSON desde Inicio
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

### Convenciones importantes

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
| `POST` | `/exports/json` | Descargar todos los datos en JSON |
| `POST` | `/backups/database` | Descargar una copia SQLite |
| `POST` | `/restores/database` | Restaurar una copia SQLite validada |

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

- [ ] Añadir historial y gráficas detalladas de peso, IMC, volumen, ejercicios, pasos y running.
- [ ] Detectar marcas personales de carga, repeticiones y volumen.
- [ ] Añadir objetivos de peso, calorías, proteína, macronutrientes y composición corporal.
- [ ] Añadir objetivos configurables de descanso, consistencia y rachas.
- [ ] Ampliar el catálogo de ejercicios con equipamiento, variantes, músculos principales/secundarios e indicaciones técnicas.
- [ ] Mejorar las validaciones, estados de carga y mensajes de error entre frontend y backend.

### Fase 3 — Cuentas, privacidad y despliegue

- [ ] Crear cuentas de usuario con registro e inicio de sesión.
- [ ] Almacenar contraseñas exclusivamente mediante hash seguro.
- [ ] Proteger la API con tokens de acceso y caducidad.
- [ ] Asociar todos los datos personales a un `user_id`.
- [ ] Garantizar que cada usuario solo puede consultar, editar, exportar o restaurar sus propios datos.
- [ ] Migrar a PostgreSQL para uso multiusuario.
- [ ] Configurar secretos con variables de entorno y desplegar mediante HTTPS.
- [ ] Permitir que varias personas usen la aplicación desde sus propios dispositivos con datos privados e independientes.

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
python -m uvicorn app.main:app --reload
```

### 5. Abrir la aplicación

- Aplicación: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### 6. Ejecutar pruebas

```bash
python -m pytest -q
```

---

## Limitaciones actuales

- Proyecto personal para un único usuario.
- Los pasos, entrenamientos, carreras y datos nutricionales se introducen manualmente.
- No hay autenticación ni sincronización en la nube.
- No hay integración actual con relojes, Apple Health, Health Connect ni dispositivos de actividad.
- Los mapas, rutas GPS e importación GPX aún no están implementados.
- El registro nutricional no sustituye orientación profesional.
- El IMC es una métrica descriptiva y no evalúa por sí solo salud ni composición corporal.

---

## Autor

Desarrollado por **Pablo Javier Montoro Bermúdez** como proyecto personal de aprendizaje y portfolio full-stack.
