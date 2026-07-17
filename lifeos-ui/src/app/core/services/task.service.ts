import { HttpClient } from '@angular/common/http';
import { Service, inject } from '@angular/core';
import { Observable, catchError } from 'rxjs';

import { environment } from '../../../environments/environment';
import { LifeTask } from '../models/task.model';
import { rethrowApiError } from './api-error.util';

export interface AddManualTaskRequest {
  label: string;
  duration_minutes: number;
  goal_id?: string;
  xp?: number;
  hour?: number;
}

export interface EditTaskRequest {
  label?: string;
  duration_minutes?: number;
  goal_id?: string;
  xp?: number;
  hour?: number;
}

export interface SkipTaskResult {
  rescheduled: boolean;
  message: string | null;
  task: LifeTask;
}

/** Task actions: complete, skip, add (manual), pull-forward, edit,
 * delete. Views (day/month/backlog) live in schedule.service.ts. */
@Service()
export class TaskService {
  private readonly http = inject(HttpClient);

  private base(playerId: string): string {
    return `${environment.apiBaseUrl}/players/${playerId}`;
  }

  addManualTask(playerId: string, body: AddManualTaskRequest): Observable<LifeTask> {
    return this.http.post<LifeTask>(`${this.base(playerId)}/tasks`, body).pipe(catchError(rethrowApiError));
  }

  completeTask(playerId: string, taskId: string): Observable<Record<string, unknown>> {
    return this.http
      .post<Record<string, unknown>>(`${this.base(playerId)}/tasks/${taskId}/complete`, {})
      .pipe(catchError(rethrowApiError));
  }

  skipTask(playerId: string, taskId: string): Observable<SkipTaskResult> {
    return this.http
      .post<SkipTaskResult>(`${this.base(playerId)}/tasks/${taskId}/skip`, {})
      .pipe(catchError(rethrowApiError));
  }

  pullTaskForward(playerId: string, taskId: string, hour?: number): Observable<LifeTask> {
    return this.http
      .post<LifeTask>(`${this.base(playerId)}/tasks/${taskId}/pull-forward`, { hour })
      .pipe(catchError(rethrowApiError));
  }

  editTask(playerId: string, taskId: string, body: EditTaskRequest): Observable<LifeTask> {
    return this.http
      .put<LifeTask>(`${this.base(playerId)}/tasks/${taskId}`, body)
      .pipe(catchError(rethrowApiError));
  }

  deleteTask(playerId: string, taskId: string): Observable<void> {
    return this.http
      .delete<void>(`${this.base(playerId)}/tasks/${taskId}`)
      .pipe(catchError(rethrowApiError));
  }
}
