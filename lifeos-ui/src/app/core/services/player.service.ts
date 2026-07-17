import { HttpClient } from '@angular/common/http';
import { Service, inject } from '@angular/core';
import { Observable, catchError, shareReplay, tap } from 'rxjs';

import { environment } from '../../../environments/environment';
import { PlayerDetail, PlayerSummary } from '../models/player.model';
import { rethrowApiError } from './api-error.util';

/** Player management: list / create / delete / fetch. The player list is
 * cached (shareReplay) since it rarely changes and several components
 * (player-select, nav-shell) want it; call refreshPlayers() after a
 * create/delete to invalidate the cache. */
@Service()
export class PlayerService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/players`;
  private playersCache$: Observable<PlayerSummary[]> | null = null;

  listPlayers(): Observable<PlayerSummary[]> {
    if (!this.playersCache$) {
      this.playersCache$ = this.http.get<PlayerSummary[]>(this.baseUrl).pipe(
        catchError(rethrowApiError),
        shareReplay(1),
      );
    }
    return this.playersCache$;
  }

  refreshPlayers(): void {
    this.playersCache$ = null;
  }

  createPlayer(name: string): Observable<PlayerDetail> {
    return this.http.post<PlayerDetail>(this.baseUrl, { name }).pipe(
      tap(() => this.refreshPlayers()),
      catchError(rethrowApiError),
    );
  }

  getPlayer(playerId: string): Observable<PlayerDetail> {
    return this.http.get<PlayerDetail>(`${this.baseUrl}/${playerId}`).pipe(catchError(rethrowApiError));
  }

  deletePlayer(playerId: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${playerId}`).pipe(
      tap(() => this.refreshPlayers()),
      catchError(rethrowApiError),
    );
  }
}
