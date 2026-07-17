import { HttpClient } from '@angular/common/http';
import { Service, inject } from '@angular/core';
import { Observable, catchError } from 'rxjs';

import { environment } from '../../../environments/environment';
import { EnergyMode, PlayerState } from '../models/player.model';
import { rethrowApiError } from './api-error.util';

export interface ModeInfo {
  energy_mode: EnergyMode;
  chaos_mode: boolean;
  comfort_mode: boolean;
  available_energy_modes: EnergyMode[];
  state: PlayerState;
}

/** Energy modes (low/normal/high), Chaos Mode, Comfort Mode, and player reset. */
@Service()
export class ModeService {
  private readonly http = inject(HttpClient);

  private base(playerId: string): string {
    return `${environment.apiBaseUrl}/players/${playerId}`;
  }

  getMode(playerId: string): Observable<ModeInfo> {
    return this.http.get<ModeInfo>(`${this.base(playerId)}/mode`).pipe(catchError(rethrowApiError));
  }

  setEnergyMode(playerId: string, mode: EnergyMode): Observable<PlayerState> {
    return this.http
      .post<PlayerState>(`${this.base(playerId)}/mode/energy`, { mode })
      .pipe(catchError(rethrowApiError));
  }

  toggleChaosMode(playerId: string): Observable<{ chaos_mode: boolean; state: PlayerState }> {
    return this.http
      .post<{ chaos_mode: boolean; state: PlayerState }>(`${this.base(playerId)}/mode/chaos/toggle`, {})
      .pipe(catchError(rethrowApiError));
  }

  toggleComfortMode(playerId: string): Observable<{ comfort_mode: boolean; state: PlayerState }> {
    return this.http
      .post<{ comfort_mode: boolean; state: PlayerState }>(`${this.base(playerId)}/mode/comfort/toggle`, {})
      .pipe(catchError(rethrowApiError));
  }

  resetPlayer(playerId: string): Observable<PlayerState> {
    return this.http.post<PlayerState>(`${this.base(playerId)}/reset`, {}).pipe(catchError(rethrowApiError));
  }
}
