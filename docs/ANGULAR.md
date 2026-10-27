# Interfaz en Angular

La interfaz actual (HTML, CSS y JavaScript en `app/frontend/`) se está pasando a
Angular **pantalla a pantalla**. El backend (FastAPI, base de datos, pruebas de
Python) no cambia: Angular solo es el frontend.

Mientras dure la migración conviven las dos:

| | Dónde vive | Dirección |
| --- | --- | --- |
| App actual | `app/frontend/` | `/`, `/static/...` |
| App nueva (Angular) | `frontend-angular/` | `/app/...` |

Las dos comparten la sesión (misma clave `fitness_tracker_access_token`) y los
mismos estilos (`/static/style.css`), así que quien inicia sesión en una ya está
dentro en la otra.

## Qué necesitas

- **Node 22.12 o superior** (con Node 24 va bien) y npm.
- La API en marcha en `http://127.0.0.1:8000` (ver el README).

La primera vez, en la carpeta `frontend-angular/`:

```bash
npm install
```

## Cómo se trabaja

Con la API arrancada (`uvicorn app.main:app --port 8000`), en otra terminal:

```bash
cd frontend-angular
npm start
```

Abre **http://localhost:4200/app/**. Cada cambio que guardes se ve al instante.
El servidor de Angular reenvía las llamadas a la API (`/auth`, `/goals`,
`/health`…) y los estilos (`/static`) a FastAPI: la lista está en
`proxy.conf.json`. Si añades un grupo de rutas nuevo a la API, añádelo ahí.

Otros comandos útiles (siempre dentro de `frontend-angular/`):

```bash
npm test                 # pruebas (Vitest), se quedan vigilando los cambios
npx ng test --watch=false  # pruebas una sola vez, como en el CI
npm run build            # compila a app/frontend-ng/ para que FastAPI lo sirva
```

Después de `npm run build`, FastAPI sirve lo compilado en
**http://localhost:8000/app/** (sin el servidor de Angular). En producción no
hay que hacer nada: la imagen Docker compila Angular sola (`Dockerfile`).

## Cómo está organizado

```
frontend-angular/
  proxy.conf.json          rutas que se reenvían a FastAPI en desarrollo
  src/
    index.html             página base (enlaza los estilos de la app actual)
    app/
      app.ts, app.html     la cabecera y el hueco donde va cada pantalla
      app.config.ts        configuración general (HttpClient, rutas)
      app.routes.ts        una línea por pantalla: dirección → componente
      core/
        auth.interceptor.ts  añade la sesión a las llamadas a la API
      pages/
        home/              inicio: ejemplo de señal + llamada a la API
        privacy/           aviso de privacidad: ejemplo de pantalla solo texto
```

Cada pantalla es una carpeta en `pages/` con su componente (`.ts`), su
plantilla (`.html`) y sus pruebas (`.spec.ts`).

## Cómo añadir una pantalla

1. Crea su carpeta y su componente: `ng generate component pages/objetivos`
   (genera los ficheros; renómbralos a `objetivos.ts`/`.html` si no te gusta el
   estilo por defecto).
2. Escribe su plantilla reutilizando las **clases de `style.css`** (`panel`,
   `intro-card`, `form-grid`, `primary-button`…). Así se ve igual que el resto.
3. Si necesita datos, llama a la API con `HttpClient` como hace `home.ts`. La
   cabecera de sesión se añade sola.
4. Registra la ruta en `app.routes.ts`.
5. Escribe sus pruebas (mira `home.spec.ts` como modelo) y ejecuta
   `npx ng test --watch=false`.
6. Cuando la pantalla nueva esté completa y probada, enlázala desde la app
   actual en lugar de la vieja y, **solo entonces**, borra los ficheros viejos.

## Orden sugerido de migración

De lo más sencillo a lo más complejo, para aprender sobre algo que se pueda
comprobar rápido:

1. Aviso de privacidad (solo texto) y inicio. *Ya hechos como ejemplo.*
2. Objetivos y pasos diarios (lectura y formularios cortos).
3. Recuperación, medidas corporales y carreras.
4. «Mi cuenta» (varios formularios, subir archivos).
5. Nutrición, biblioteca de alimentos y entrenamientos.
6. Calendario, la pantalla más grande, al final.

## Reglas para no romper nada

- **No se toca la API** para migrar una pantalla. Si hace falta un endpoint
  nuevo, es un cambio aparte.
- **Los textos de la interfaz, en español.**
- **El token nunca sale hacia otro dominio:** el interceptor solo lo añade a
  rutas que empiezan por `/` (nuestra API). No lo cambies sin hablarlo.
- Una pantalla vieja no se borra hasta que la nueva funciona y tiene pruebas.
- Cada pantalla, una PR.

## Para aprender

- Tutorial oficial: <https://angular.dev/tutorials>
- Conceptos que irás usando, en este orden: componentes y plantillas, señales
  (`signal`), `@if` y `@for`, `HttpClient`, formularios, rutas.
- Mira `src/app/pages/home/home.ts`: es el ejemplo más pequeño con estado y una
  llamada a la API, y está comentado.
