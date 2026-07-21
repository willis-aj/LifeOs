import { HttpClient } from '@angular/common/http';
import { Service, inject } from '@angular/core';
import { Observable, catchError } from 'rxjs';

import { environment } from '../../../environments/environment';
import { Routine } from '../models/routine.model';
import { rethrowApiError } from './api-error.util';

export interface AddRoutineRequest {
  label: string;
  goal_id?: string;
  duration_minutes?: number;
  xp?: number;
  frequency?: string; // "daily" | "weekly" | "monthly"
  boss?: boolean;
  note_template?: string;
}

/** A player's routines (definitions + completion history) - brushing
 * teeth, meds, raids, scheduling tasks, and so on - plus creating new
 * ones from the task-completion popup's "create new event or routine"
 * form. */
@Service()
export class RoutineService {
  private readonly http = inject(HttpClient);

  private base(playerId: string): string {
    return `${environment.apiBaseUrl}/players/${playerId}/routines`;
  }

  listRoutines(playerId: string): Observable<Routine[]> {
    return this.http.get<Routine[]>(this.base(playerId)).pipe(catchError(rethrowApiError));
  }

  addRoutine(playerId: string, body: AddRoutineRequest): Observable<Routine> {
    return this.http.post<Routine>(this.base(playerId), body).pipe(catchError(rethrowApiError));
  }
}
