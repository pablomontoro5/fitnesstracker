import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

/**
 * Aviso de privacidad. Es la pantalla más sencilla: solo texto, sin lógica.
 * Su contenido es el de `app/frontend/privacy/index.html`; cuando se decida
 * quedarse con la versión de Angular, se borra la antigua.
 */
@Component({
  selector: 'app-privacy',
  imports: [RouterLink],
  templateUrl: './privacy.html',
})
export class Privacy {}
