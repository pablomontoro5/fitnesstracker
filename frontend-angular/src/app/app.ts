import { Component } from '@angular/core';
import { RouterLink, RouterOutlet } from '@angular/router';

/** Componente raíz: la cabecera de siempre y, debajo, la pantalla de cada ruta. */
@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink],
  templateUrl: './app.html',
})
export class App {}
