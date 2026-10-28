import { Routes } from '@angular/router';

import { Home } from './pages/home/home';
import { Privacy } from './pages/privacy/privacy';

/**
 * Una ruta por pantalla migrada. Para añadir una:
 *   1. crea su componente en `pages/<nombre>/`;
 *   2. añade aquí una línea con su `path` y su `title`.
 * Las rutas que no existan vuelven al inicio.
 */
export const routes: Routes = [
  { path: '', component: Home, title: 'Fitness Tracker (nueva interfaz)' },
  { path: 'privacidad', component: Privacy, title: 'Privacidad | Fitness Tracker' },
  { path: '**', redirectTo: '' },
];
