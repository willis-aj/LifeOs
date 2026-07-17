import { HttpClient } from '@angular/common/http';
import { Service, inject } from '@angular/core';
import { Observable, catchError, shareReplay } from 'rxjs';

import { environment } from '../../../environments/environment';
import { rethrowApiError } from './api-error.util';

export interface CompanionSummary {
  id: string;
  name: string;
  personality: string;
}

export interface CurrentCompanion {
  companion_id: string;
  message: string;
}

/** Companions and seasons: the global rosters (config-driven, cached
 * since they never change at runtime) plus a player's current selection. */
@Service()
export class CompanionService {
  private readonly http = inject(HttpClient);
  private companionsCache$: Observable<CompanionSummary[]> | null = null;

  listCompanions(): Observable<CompanionSummary[]> {
    if (!this.companionsCache$) {
      this.companionsCache$ = this.http
        .get<CompanionSummary[]>(`${environment.apiBaseUrl}/companions`)
        .pipe(catchError(rethrowApiError), shareReplay(1));
    }
    return this.companionsCache$;
  }

  getCurrentCompanion(playerId: string): Observable<CurrentCompanion> {
    return this.http
      .get<CurrentCompanion>(`${environment.apiBaseUrl}/players/${playerId}/companion`)
      .pipe(catchError(rethrowApiError));
  }

  setCompanion(playerId: string, companionId: string): Observable<CurrentCompanion> {
    return this.http
      .post<CurrentCompanion>(`${environment.apiBaseUrl}/players/${playerId}/companion`, {
        companion_id: companionId,
      })
      .pipe(catchError(rethrowApiError));
  }
}
