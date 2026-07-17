import { HttpClient } from '@angular/common/http';
import { Service, inject } from '@angular/core';
import { Observable, catchError } from 'rxjs';

import { environment } from '../../../environments/environment';
import { LifeTask } from '../models/task.model';
import { rethrowApiError } from './api-error.util';

export interface CreateScheduledEventRequest {
  date: string; // ISO date, "YYYY-MM-DD"
  label?: string;
  hour?: number;
  duration_minutes?: number;
  goal_id?: string;
  boss?: boolean;
}

/** Creates the "actual event" a user schedules after completing a
 * scheduling-type task (e.g. the real dinner/raid/appointment). */
@Service()
export class EventService {
  private readonly http = inject(HttpClient);

  createScheduledEvent(playerId: string, body: CreateScheduledEventRequest): Observable<LifeTask> {
    return this.http
      .post<LifeTask>(`${environment.apiBaseUrl}/players/${playerId}/events`, body)
      .pipe(catchError(rethrowApiError));
  }
}
