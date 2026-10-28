"""Servir una aplicación de una sola página (la de Angular) desde FastAPI."""
from pathlib import PurePosixPath

from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles


class SinglePageApp(StaticFiles):
    """Sirve los ficheros compilados y, para las rutas de pantalla, `index.html`.

    Angular decide en el navegador qué pantalla enseñar según la dirección. Si
    alguien recarga `/app/privacidad`, el servidor no tiene ningún fichero con
    ese nombre: devolvemos `index.html` y Angular hace el resto.

    Los ficheros que sí llevan extensión (`main-XXXX.js`, imágenes…) no hacen
    fallback: un fichero que falta debe dar 404 y no una página HTML que el
    navegador intentaría ejecutar como JavaScript.
    """

    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            if error.status_code != 404 or PurePosixPath(path).suffix:
                raise

            return await super().get_response("index.html", scope)
