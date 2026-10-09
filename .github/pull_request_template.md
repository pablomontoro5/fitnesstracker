## Qué cambia

<!-- Resumen en 2-4 líneas o viñetas. Qué se añade, cambia o elimina. -->

## Por qué

<!-- El problema o la necesidad que motiva el cambio. -->

## Cómo se ha probado

<!-- Marca lo que hayas hecho y añade el resultado (nº de tests, comando, etc.). -->

- [ ] `pytest` en verde
- [ ] Probado en el navegador (si toca el frontend)
- [ ] Probado con `docker build` + `docker run --env-file` (si toca el despliegue)

## Para revisar

<!-- Riesgos, decisiones discutibles, cosas que no se han hecho, orden de despliegue. -->

## Lista de comprobación

- [ ] Si cambia el esquema: migración **nueva** en `MIGRATIONS` (no se edita una ya aplicada) y RLS activado en las tablas nuevas
- [ ] No se añaden secretos (contraseñas, cadena de conexión, JWT) al repositorio, ni a logs
- [ ] Textos de la interfaz y documentación en español
