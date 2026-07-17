import { HttpClient } from '@angular/common/http';
import { Service, inject } from '@angular/core';
import { Observable, catchError } from 'rxjs';

import { environment } from '../../../environments/environment';
import { Routine } from '../models/routine.model';
import { rethrowApiError } from './api-error.util';

/** Read-only view of a player's routines (definitions + completion
 * history) - brushing teeth, meds, raids, scheduling tasks, and so on. */
@Service()
export class RoutineService {
  private readonly http = inject(HttpClient);

  listRoutines(playerId: string): Observable<Routine[]> {
    return this.http
      .get<Routine[]>(`${environment.apiBaseUrl}/players/${playerId}/routines`)
      .pipe(catchError(rethrowApiError));
  }
}
