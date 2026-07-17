import { HttpClient } from '@angular/common/http';
import { Service, inject } from '@angular/core';
import { Observable, catchError } from 'rxjs';

import { environment } from '../../../environments/environment';
import { AddGoalRequest, EditGoalRequest, GoalProgress } from '../models/goal.model';
import { rethrowApiError } from './api-error.util';

/** Goal management: list / add / edit / delete - mirrors the CLI's
 * "edit goals" menu. */
@Service()
export class GoalService {
  private readonly http = inject(HttpClient);

  private base(playerId: string): string {
    return `${environment.apiBaseUrl}/players/${playerId}/goals`;
  }

  listGoals(playerId: string): Observable<GoalProgress[]> {
    return this.http.get<GoalProgress[]>(this.base(playerId)).pipe(catchError(rethrowApiError));
  }

  addGoal(playerId: string, body: AddGoalRequest): Observable<GoalProgress> {
    return this.http.post<GoalProgress>(this.base(playerId), body).pipe(catchError(rethrowApiError));
  }

  editGoal(playerId: string, goalId: string, body: EditGoalRequest): Observable<GoalProgress> {
    return this.http
      .put<GoalProgress>(`${this.base(playerId)}/${goalId}`, body)
      .pipe(catchError(rethrowApiError));
  }

  deleteGoal(playerId: string, goalId: string): Observable<void> {
    return this.http.delete<void>(`${this.base(playerId)}/${goalId}`).pipe(catchError(rethrowApiError));
  }
}
