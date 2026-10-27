import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ACCESS_TOKEN_KEY, authInterceptor } from './auth.interceptor';

describe('authInterceptor', () => {
  let client: HttpClient;
  let http: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
      ],
    });

    client = TestBed.inject(HttpClient);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => localStorage.clear());

  it('añade la cabecera de sesión a las peticiones a nuestra API', () => {
    localStorage.setItem(ACCESS_TOKEN_KEY, 'abc123');

    client.get('/goals').subscribe();

    const request = http.expectOne('/goals');
    expect(request.request.headers.get('Authorization')).toBe('Bearer abc123');
  });

  it('no añade cabecera si no hay sesión', () => {
    client.get('/health').subscribe();

    const request = http.expectOne('/health');
    expect(request.request.headers.has('Authorization')).toBe(false);
  });

  it('nunca manda el token a otro dominio', () => {
    localStorage.setItem(ACCESS_TOKEN_KEY, 'abc123');

    client.get('https://otro-dominio.example/datos').subscribe();

    const request = http.expectOne('https://otro-dominio.example/datos');
    expect(request.request.headers.has('Authorization')).toBe(false);
  });

  it('respeta una cabecera de autorización ya puesta', () => {
    localStorage.setItem(ACCESS_TOKEN_KEY, 'abc123');

    client.get('/goals', { headers: { Authorization: 'Bearer otro' } }).subscribe();

    const request = http.expectOne('/goals');
    expect(request.request.headers.get('Authorization')).toBe('Bearer otro');
  });
});
