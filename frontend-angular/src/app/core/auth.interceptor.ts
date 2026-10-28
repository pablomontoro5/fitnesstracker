import { HttpInterceptorFn } from '@angular/common/http';
import { tap } from 'rxjs';

/**
 * Misma clave que usa la app actual (`auth.js`): así la sesión es compartida y
 * quien ya ha iniciado sesión no tiene que volver a hacerlo.
 */
export const ACCESS_TOKEN_KEY = 'fitness_tracker_access_token';

export function readAccessToken(): string | null {
  try {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  } catch {
    // Sin almacenamiento (modo privado, por ejemplo): se trata como sin sesión.
    return null;
  }
}

function clearAccessToken(): void {
  try {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
  } catch {
    // Nada que borrar.
  }
}

/**
 * Añade la cabecera `Authorization` a las peticiones a nuestra API y, si el
 * servidor responde 401 (sesión caducada o inválida), lleva al inicio de sesión.
 */
export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const token = readAccessToken();

  // Solo rutas relativas (nuestra API): el token nunca sale hacia otro dominio.
  const isOurApi = request.url.startsWith('/');
  const outgoing =
    token && isOurApi && !request.headers.has('Authorization')
      ? request.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
      : request;

  return next(outgoing).pipe(
    tap({
      error: (error) => {
        if (error.status === 401 && token && isOurApi) {
          clearAccessToken();
          const next = encodeURIComponent(window.location.pathname);
          window.location.assign(`/static/login/?next=${next}`);
        }
      },
    }),
  );
};
