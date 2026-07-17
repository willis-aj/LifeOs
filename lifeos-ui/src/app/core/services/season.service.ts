import { HttpClient } from '@angular/common/http';
import { Service, inject } from '@angular/core';
import { Observable, catchError, shareReplay } from 'rxjs';

import { environment } from '../../../environments/environment';
import { rethrowApiError } from './api-error.util';

export interface SeasonSummary {
  id: string;
  label: string;
  duration_days: number;
}

export interface CurrentSeason {
  id: string | null;
  label: string | null;
}

/** Seasons: the global roster (config-driven, cached) plus a player's
 * current season. */
@Service()
export class SeasonService {
  private readonly http = inject(HttpClient);
  private seasonsCache$: Observable<SeasonSummary[]> | null = null;

  listSeasons(): Observable<SeasonSummary[]> {
    if (!this.seasonsCache$) {
      this.seasonsCache$ = this.http
        .get<SeasonSummary[]>(`${environment.apiBaseUrl}/seasons`)
        .pipe(catchError(rethrowApiError), shareReplay(1));
    }
    return this.seasonsCache$;
  }

  getCurrentSeason(playerId: string): Observable<CurrentSeason> {
    return this.http
      .get<CurrentSeason>(`${environment.apiBaseUrl}/players/${playerId}/season`)
      .pipe(catchError(rethrowApiError));
  }
}
