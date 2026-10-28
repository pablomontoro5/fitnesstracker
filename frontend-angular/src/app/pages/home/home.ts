import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

type ServerState = 'loading' | 'ok' | 'error';

/**
 * Pantalla de inicio. Sirve de ejemplo de lo básico:
 *  - una señal (`signal`) para el estado de la pantalla;
 *  - una llamada a la API con `HttpClient`;
 *  - una plantilla que cambia según ese estado.
 */
@Component({
  selector: 'app-home',
  imports: [RouterLink],
  templateUrl: './home.html',
})
export class Home implements OnInit {
  private readonly http = inject(HttpClient);

  protected readonly server = signal<ServerState>('loading');

  ngOnInit(): void {
    this.http.get<{ status: string }>('/health').subscribe({
      next: (response) => this.server.set(response.status === 'ok' ? 'ok' : 'error'),
      error: () => this.server.set('error'),
    });
  }
}
