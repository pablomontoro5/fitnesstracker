# Interfaz en Angular

Esta carpeta es la nueva interfaz de Fitness Tracker, que va sustituyendo poco a
poco a la de `app/frontend/`. El backend (FastAPI) no cambia.

Todo lo necesario para trabajar aquí (cómo arrancarla, cómo está organizada,
cómo añadir una pantalla y el orden de migración) está en
[`../docs/ANGULAR.md`](../docs/ANGULAR.md).

Resumen rápido:

```bash
npm install     # la primera vez
npm start       # http://localhost:4200/app/ (con la API en el 8000)
npm test        # pruebas
npm run build   # compila a ../app/frontend-ng/ para que FastAPI lo sirva
```
