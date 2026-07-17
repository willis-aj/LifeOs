import { HttpClient, HttpParams } from '@angular/common/http';
import { Service, inject } from '@angular/core';
import { Observable, catchError } from 'rxjs';

import { environment } from '../../../environments/environment';
import { BacklogView, HourGroup, LifeTask, MonthCalendarView } from '../models/task.model';
import { rethrowApiError } from './api-error.util';

export interface HomeView {
  player_id: string;
  player_name: string;
  state: import('../models/player.model').PlayerState;
  companion_message: string;
  current_hour: number;
  current_hour_tasks: LifeTask[];
  checkin: import('../models/player.model').CheckinSummary | null;
}

/** Read-side views of the schedule: home dashboard, hour/day/month/backlog. */
@Service()
export class ScheduleService {
  private readonly http = inject(HttpClient);

  private base(playerId: string): string {
    return `${environment.apiBaseUrl}/players/${playerId}`;
  }

  getHome(playerId: string): Observable<HomeView> {
    return this.http.get<HomeView>(`${this.base(playerId)}/home`).pipe(catchError(rethrowApiError));
  }

  getHour(playerId: string, hour?: number): Observable<{ hour: number; tasks: LifeTask[] }> {
    let params = new HttpParams();
    if (hour !== undefined) {
      params = params.set('hour', hour);
    }
    return this.http
      .get<{ hour: number; tasks: LifeTask[] }>(`${this.base(playerId)}/hour`, { params })
      .pipe(catchError(rethrowApiError));
  }

  getDay(playerId: string): Observable<HourGroup[]> {
    return this.http.get<HourGroup[]>(`${this.base(playerId)}/day`).pipe(catchError(rethrowApiError));
  }

  getMonth(playerId: string, year?: number, month?: number): Observable<MonthCalendarView> {
    let params = new HttpParams();
    if (year !== undefined) params = params.set('year', year);
    if (month !== undefined) params = params.set('month', month);
    return this.http
      .get<MonthCalendarView>(`${this.base(playerId)}/month`, { params })
      .pipe(catchError(rethrowApiError));
  }

  getBacklog(playerId: string): Observable<BacklogView> {
    return this.http.get<BacklogView>(`${this.base(playerId)}/backlog`).pipe(catchError(rethrowApiError));
  }
}
