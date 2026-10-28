import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { Privacy } from './privacy';

describe('Privacy', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Privacy],
      providers: [provideRouter([])],
    }).compileComponents();
  });

  it('muestra los apartados del aviso', () => {
    const fixture = TestBed.createComponent(Privacy);
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';

    for (const title of [
      'Quién es el responsable',
      'Qué datos guardamos',
      'Tus derechos y cómo ejercerlos',
    ]) {
      expect(text).toContain(title);
    }
  });

  it('mantiene visibles los huecos que debe rellenar el responsable', () => {
    const fixture = TestBed.createComponent(Privacy);
    fixture.detectChanges();

    expect((fixture.nativeElement as HTMLElement).textContent).toContain(
      '[EMAIL DE CONTACTO]',
    );
  });
});
