import { HttpClient } from '@angular/common/http';
import { Service, inject } from '@angular/core';
import { Observable, catchError } from 'rxjs';

import { environment } from '../../../environments/environment';
import { rethrowApiError } from './api-error.util';

export interface InventoryItem {
  id: string;
  label: string;
  rarity: string;
}

/** Read-only view of a player's loot inventory. */
@Service()
export class InventoryService {
  private readonly http = inject(HttpClient);

  getInventory(playerId: string): Observable<InventoryItem[]> {
    return this.http
      .get<InventoryItem[]>(`${environment.apiBaseUrl}/players/${playerId}/inventory`)
      .pipe(catchError(rethrowApiError));
  }
}
