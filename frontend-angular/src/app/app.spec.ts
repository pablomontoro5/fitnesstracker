import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { App } from './app';

describe('App', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideRouter([])],
    }).compileComponents();
  });

  it('se crea', () => {
    const fixture = TestBed.createComponent(App);

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('muestra la cabecera con el enlace a la app actual', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const element = fixture.nativeElement as HTMLElement;

    const oldAppLink = Array.from(element.querySelectorAll('a')).find((link) =>
      link.textContent?.includes('app actual'),
    );

    expect(element.querySelector('h1')?.textContent).toContain('Nueva interfaz');
    expect(oldAppLink?.getAttribute('href')).toBe('/');
  });
});
