import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { Home } from './home';

describe('Home', () => {
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Home],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    http = TestBed.inject(HttpTestingController);
  });

  async function render(): Promise<HTMLElement> {
    const fixture = TestBed.createComponent(Home);
    fixture.detectChanges();

    return fixture.nativeElement as HTMLElement;
  }

  it('muestra «Comprobando» mientras espera al servidor', async () => {
    const element = await render();

    expect(element.textContent).toContain('Comprobando');
    http.expectOne('/health');
  });

  it('indica que el servidor funciona si /health responde ok', async () => {
    const fixture = TestBed.createComponent(Home);
    fixture.detectChanges();

    http.expectOne('/health').flush({ status: 'ok', database: 'ok' });
    fixture.detectChanges();

    expect((fixture.nativeElement as HTMLElement).textContent).toContain(
      'El servidor responde',
    );
  });

  it('avisa si /health falla', async () => {
    const fixture = TestBed.createComponent(Home);
    fixture.detectChanges();

    http
      .expectOne('/health')
      .flush({ status: 'error' }, { status: 503, statusText: 'Service Unavailable' });
    fixture.detectChanges();

    expect((fixture.nativeElement as HTMLElement).textContent).toContain(
      'No se pudo comprobar el servidor',
    );
  });

  it('enlaza a las pantallas migradas', async () => {
    const element = await render();

    expect(element.querySelector('a[href="/privacidad"]')).toBeTruthy();
    http.expectOne('/health');
  });
});
