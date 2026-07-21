import { HttpClient } from '@angular/common/http';
import { Service, inject } from '@angular/core';
import { Observable, catchError } from 'rxjs';

import { environment } from '../../../environments/environment';
import { SelfCareStatus } from '../models/self-care.model';
import { rethrowApiError } from './api-error.util';

/** Read-only status from the Self-Care Agent: today's gentle nudges plus
 * whether Comfort Mode is worth suggesting. Everything the panel offers
 * to *do* (complete a task, toggle Comfort Mode) goes through TaskService /
 * ModeService as usual - this service only reports. The conversational
 * counterpart lives in chat.service.ts. */
@Service()
export class SelfCareService {
  private readonly http = inject(HttpClient);

  getStatus(playerId: string): Observable<SelfCareStatus> {
    return this.http
      .get<SelfCareStatus>(`${environment.apiBaseUrl}/players/${playerId}/self-care/status`)
      .pipe(catchError(rethrowApiError));
  }
}
