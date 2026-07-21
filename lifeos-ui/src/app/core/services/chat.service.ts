import { HttpClient } from '@angular/common/http';
import { Service, inject } from '@angular/core';
import { Observable, catchError } from 'rxjs';

import { environment } from '../../../environments/environment';
import { ChatResponse } from '../models/chat.model';
import { rethrowApiError } from './api-error.util';

/** The Self-Care Agent's conversational front-end: send a free-text
 * message, get back the new messages (the user's own turn plus every
 * system/agent reply), and fetch the full transcript. A message may
 * silently create a real routine/task or toggle Comfort Mode server-side -
 * this service just carries text back and forth. */
@Service()
export class ChatService {
  private readonly http = inject(HttpClient);

  private base(playerId: string): string {
    return `${environment.apiBaseUrl}/players/${playerId}/self-care`;
  }

  sendMessage(playerId: string, message: string): Observable<ChatResponse> {
    return this.http
      .post<ChatResponse>(`${this.base(playerId)}/chat`, { message })
      .pipe(catchError(rethrowApiError));
  }

  getHistory(playerId: string): Observable<ChatResponse> {
    return this.http.get<ChatResponse>(`${this.base(playerId)}/history`).pipe(catchError(rethrowApiError));
  }
}
