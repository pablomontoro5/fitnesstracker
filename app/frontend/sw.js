// Service worker de Fitness Tracker. Se sirve en /sw.js (ámbito "/").
//
// Qué guarda: solo ficheros estáticos de /static/ y la página de inicio, para
// que la aplicación se pueda instalar y abra algo aunque no haya conexión.
// Qué NO guarda nunca: respuestas de la API. Llevan datos de salud y no deben
// quedar en la caché del dispositivo (podría ser compartido): esas peticiones
// ni siquiera se interceptan y van directas a la red.
//
// Estrategia: primero la red y, si falla, la copia guardada. Así, con conexión,
// siempre se ve la versión desplegada más reciente.

const CACHE_VERSION = "v1";
const CACHE_NAME = `fitness-tracker-${CACHE_VERSION}`;
const OFFLINE_HTML = `<!doctype html>
<html lang="es"><head><meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Sin conexión | Fitness Tracker</title>
<style>body{font-family:system-ui,sans-serif;margin:0;min-height:100vh;display:grid;
place-items:center;background:#f4f7f5;color:#17231d;text-align:center;padding:1.5rem}
h1{margin:0 0 .5rem}p{color:#62736a}</style></head>
<body><main><h1>Sin conexión</h1>
<p>No se puede cargar esta página ahora mismo. Comprueba tu conexión y vuelve a intentarlo.</p>
</main></body></html>`;

function isCacheable(url) {
  return url.origin === self.location.origin
    && (url.pathname === "/" || url.pathname.startsWith("/static/")
        || url.pathname === "/manifest.webmanifest");
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(["/", "/static/style.css", "/static/auth.js"]))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(
        names
          .filter((name) => name.startsWith("fitness-tracker-") && name !== CACHE_NAME)
          .map((name) => caches.delete(name)),
      ))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;

  if (request.method !== "GET") {
    return;
  }

  const url = new URL(request.url);

  if (!isCacheable(url)) {
    return; // API y todo lo demás: directo a la red, sin copia.
  }

  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        }

        return response;
      })
      .catch(() => caches.match(request).then((cached) => {
        if (cached) {
          return cached;
        }

        if (request.mode === "navigate") {
          return new Response(OFFLINE_HTML, {
            status: 503,
            headers: { "Content-Type": "text/html; charset=utf-8" },
          });
        }

        return Response.error();
      })),
  );
});
