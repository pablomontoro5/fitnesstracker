# Fitness Tracker — Health & Training Log 🏋️‍♂️🏃‍♂️

**Fitness Tracker** es una aplicación web personal para centralizar el seguimiento diario de actividad, entrenamientos de gimnasio, running, alimentación y composición corporal.

El proyecto nace con una arquitectura incremental, inspirada en *Virtual Wardrobe Weather*: backend modular con FastAPI, persistencia local con SQLite, API documentada automáticamente, pruebas y un frontend sencillo. La primera meta es una aplicación web funcional y responsive; posteriormente podrá evolucionar a una experiencia móvil para iOS mediante una PWA o un cliente nativo conectado a la misma API.

---

## Objetivo

Registrar en un único lugar los datos que normalmente quedan repartidos entre notas, hojas de cálculo y varias aplicaciones:

- Pasos diarios y actividad general.
- Rutinas de gimnasio por sesión, ejercicio, serie, repeticiones, carga y RIR.
- Seguimiento de progreso por ejercicio y notas técnicas.
- Sesiones de running con distancia, duración, ritmo medio por kilómetro y recorrido.
- Comidas y resumen nutricional diario.
- Peso, altura, IMC y evolución corporal.

La captura de referencia muestra una rutina de empujes basada en series con rangos de repeticiones, carga, RIR y observaciones. El módulo de gimnasio se diseñará para reflejar esa forma de entrenar, sin obligar a usar una plantilla cerrada.

---

## Alcance del MVP

La versión inicial estará enfocada en un solo usuario y funcionamiento local. No incluirá todavía autenticación, sincronización con relojes, conteo automático de calorías ni mapas interactivos completos.

### Registro diario

- Crear o consultar un día de seguimiento.
- Registrar pasos y notas generales.
- Ver un resumen de actividad, entrenamiento, nutrición y peso del día.

### Gimnasio

- Crear plantillas de rutina, por ejemplo: `Empujes`, `Tirón` y `Pierna`.
- Añadir ejercicios a una sesión con grupo muscular, orden y notas técnicas.
- Registrar cada serie con objetivo de repeticiones, repeticiones realizadas, carga, RIR y observaciones.
- Registrar calentamiento y aproximaciones opcionales.
- Consultar el historial de un ejercicio y su progreso básico de carga, repeticiones y volumen.

### Running

- Registrar fecha, distancia total, duración, ritmo medio y notas.
- Guardar un recorrido opcional como puntos GPS o archivo GPX para habilitar mapas más adelante.
- Mostrar el historial de sesiones y métricas simples de evolución.

### Alimentación y cuerpo

- Crear comidas y añadir alimentos manualmente.
- Guardar calorías y macronutrientes cuando estén disponibles.
- Registrar peso y altura.
- Calcular el IMC como referencia: `peso_kg / altura_m²`.
- Mostrar la evolución del peso e IMC.

---

## Decisiones de producto

- **Web primero y móvil después:** el frontend será responsive desde el inicio. Una PWA permitirá instalar la aplicación en iPhone más adelante sin duplicar el backend.
- **Datos propios y editables:** todos los registros creados por el usuario podrán consultarse, corregirse y eliminarse.
- **Registro rápido:** introducir una serie o una sesión debe requerir pocos campos; los detalles como notas, GPS o macronutrientes serán opcionales.
- **Sin afirmaciones médicas:** peso e IMC se muestran como métricas de seguimiento, no como diagnóstico o recomendación sanitaria.

---

## Tecnologías

### Backend

- Python
- FastAPI
- SQLite mediante `sqlite3` durante el MVP
- Pydantic para validación de datos
- Pytest para pruebas

### Frontend

- HTML
- CSS
- JavaScript
- Diseño responsive orientado a móvil

### Evolución prevista

- Leaflet + OpenStreetMap para visualizar rutas de running.
- Importación GPX.
- PWA (manifest y service worker).
- PostgreSQL cuando exista necesidad de despliegue multiusuario o mayor concurrencia.

FastAPI ofrecerá documentación interactiva en `/docs` y `/redoc`.

---

## Estructura inicial

```text
fitness-tracker/
├── app/
│   ├── main.py
│   ├── db.py
│   ├── schemas.py
│   ├── routers/
│   │   ├── daily_logs.py
│   │   ├── body_metrics.py
│   │   ├── workout_sessions.py
│   │   └── workout_exercises.py
│   └── frontend/
│       ├── index.html
│       ├── style.css
│       └── app.js
├── tests/
│   ├── test_daily_logs.py
│   ├── test_body_metrics.py
│   ├── test_workout_sessions.py
│   └── test_workout_exercises.py
```

Los routers mantienen los endpoints separados por dominio. Los servicios alojan cálculos reutilizables, como volumen de entrenamiento, ritmo de carrera e IMC, para que sean fáciles de probar sin depender de la API.

---

## Modelo de datos inicial

| Entidad | Campos principales |
| --- | --- |
| `daily_logs` | `id`, `date`, `steps`, `notes` |
| `workout_templates` | `id`, `name`, `description` |
| `exercise_templates` | `id`, `workout_template_id`, `name`, `muscle_group`, `position`, `technique_notes` |
| `workout_sessions` | `id`, `date`, `name`, `notes` |
| `workout_exercises` | `id`, `workout_session_id`, `exercise_name`, `muscle_group`, `position` |
| `workout_sets` | `id`, `workout_exercise_id`, `set_type`, `target_rep_range`, `repetitions`, `weight_kg`, `rir`, `notes` |
| `runs` | `id`, `date`, `distance_km`, `duration_seconds`, `average_pace_seconds_km`, `notes`, `route_data` |
| `meals` | `id`, `date`, `meal_type`, `name`, `calories`, `protein_g`, `carbs_g`, `fat_g` |
| `body_metrics` | `id`, `date`, `weight_kg`, `height_cm`, `bmi`, `notes` |

### Convenciones importantes

- `weight_kg` será un número decimal; las cargas de gimnasio se guardarán en kilogramos.
- `duration_seconds` y `average_pace_seconds_km` evitan errores al ordenar o calcular tiempos.
- `rir` representa *reps in reserve*; puede ser decimal o nulo si no se registra.
- `set_type` permitirá diferenciar `warmup`, `approximation`, `working` y `drop_set`.
- `route_data` se mantendrá opcional y se definirá como JSON o referencia a un GPX en una fase posterior.

---

## Cálculos del MVP

- **IMC:** `peso_kg / (altura_cm / 100)²`.
- **Ritmo medio:** `duración total en segundos / distancia en km`.
- **Volumen de una serie:** `repeticiones × carga_kg`.
- **Volumen de un ejercicio/sesión:** suma de los volúmenes de sus series de trabajo.

Ejemplo: una serie de 10 repeticiones con 50 kg aporta 500 kg de volumen. El RIR se almacenará junto a la serie, pero no alterará este cálculo básico.

---

## Endpoints previstos

| Método | Endpoint | Propósito | Estado |
| --- | --- | --- | --- |
| `GET` / `POST` | `/daily-logs/` | Consultar o crear registros diarios | Implementado |
| `GET` / `PUT` / `DELETE` | `/daily-logs/{id}` | Consultar, editar o borrar un día | Implementado |
| `GET` / `POST` | `/body-metrics/` | Consultar o registrar peso, altura e IMC | Implementado |
| `GET` / `POST` | `/workout-sessions/` | Listar o crear sesiones de gimnasio | Implementado |
| `GET` / `PUT` / `DELETE` | `/workout-sessions/{session_id}` | Consultar, editar o eliminar una sesión | Implementado |
| `POST` | `/workout-sessions/{session_id}/exercises/` | Añadir un ejercicio a una sesión | Implementado |
| `GET` | `/workout-sessions/{session_id}/exercises/` | Listar ejercicios de una sesión por posición | Implementado |
| `GET` / `DELETE` | `/workout-exercises/{exercise_id}` | Consultar o eliminar un ejercicio | Implementado |
| `POST` | `/workout-exercises/{exercise_id}/sets/` | Añadir una serie a un ejercicio | Próximamente |
| `GET` | `/workouts/progress` | Obtener progreso por ejercicio | Próximamente |
| `GET` / `POST` | `/runs/` | Listar o registrar sesiones de running | Próximamente |
| `GET` / `POST` | `/meals/` | Listar o registrar comidas | Próximamente |

Los nombres y campos exactos pueden evolucionar, pero se mantendrá una API coherente y documentada.

---

## Roadmap

### Fase 1 — Base funcional

- [x] Crear proyecto FastAPI, SQLite e inicialización de tablas.
- [x] Añadir registro diario de pasos.
- [~] Implementar sesiones de gimnasio.
- [x] Añadir ejercicios ordenados dentro de una sesión.
- [ ] Añadir series de gimnasio con tipo, repeticiones, carga y RIR.
- [x] Implementar registro de peso, altura e IMC.
- [ ] Crear frontend mínimo con navegación y formularios.
- [~] Añadir pruebas de endpoints y cálculos.

### Fase 2 — Seguimiento útil

- [ ] Plantillas de rutinas y duplicación de entrenamientos.
- [ ] Historial y gráficos simples de peso, volumen y ejercicios.
- [ ] Registro de running con distancia, duración y ritmo.
- [ ] Registro de comidas y totales diarios de macronutrientes.
- [ ] Validación clara entre frontend y backend.

### Fase 3 — Rutas y experiencia móvil

- [ ] Importación GPX y mapa de recorrido con Leaflet.
- [ ] Instalación como PWA en iOS.
- [ ] Modo sin conexión básico y sincronización al recuperar red.
- [ ] Exportación de datos personales a CSV/JSON.

### Fase 4 — Integraciones y personalización

- [ ] Integración opcional con Apple Health, Health Connect o fuentes equivalentes, previa revisión de permisos y privacidad.
- [ ] Objetivos personalizados de pasos, peso, nutrición y entrenamiento.
- [ ] Panel de tendencias y alertas configurables.

---

## Puesta en marcha

### 1. Clonar el repositorio

```bash
git clone https://github.com/YOUR_USERNAME/fitness-tracker.git
cd fitness-tracker
```

### 2. Crear entorno virtual

```bash
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows:

```bash
.venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Ejecutar la aplicación

```bash
uvicorn app.main:app --reload
```

### 5. Abrir documentación

- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### 6. Ejecutar pruebas

```bash
python -m pytest
```

---

## Próximo incremento recomendado

El primer corte vertical implementará un flujo completo de gimnasio:

1. Crear una sesión `Empujes`.
2. Añadir un ejercicio, por ejemplo `Press inclinado con mancuernas`.
3. Añadir sus series de aproximación y trabajo, con repeticiones, carga y RIR.
4. Consultar la sesión en el frontend y calcular su volumen total.

Este flujo valida base de datos, API, validación, interfaz y la estructura necesaria para extender después a pasos, running, comidas y métricas corporales.

---

## Limitaciones iniciales

- Proyecto personal y de un único usuario.
- Los pasos se introducen manualmente durante el MVP.
- El registro nutricional no sustituye orientación profesional.
- Los mapas y datos GPS no forman parte de la primera versión.
- El IMC es una métrica descriptiva y no evalúa por sí solo salud ni composición corporal.

---

## Autor

Desarrollado por **Pablo Javier Montoro Bermúdez** como proyecto personal de aprendizaje y portfolio full-stack.
