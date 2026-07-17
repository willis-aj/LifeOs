import { HttpErrorResponse } from '@angular/common/http';
import { throwError } from 'rxjs';

/** A normalized, user-displayable error surfaced by every service in this
 * app - so components never have to know about HttpErrorResponse shapes. */
export interface ApiError {
  status: number;
  message: string;
}

/** Turns any HttpErrorResponse into an ApiError with a readable message,
 * preferring FastAPI's {"detail": "..."} body when present. */
export function toApiError(error: HttpErrorResponse): ApiError {
  const detail = (error.error && (error.error as { detail?: string }).detail) || undefined;
  if (error.status === 0) {
    return { status: 0, message: 'Cannot reach the LifeOS API. Is it running?' };
  }
  return {
    status: error.status,
    message: detail || error.message || `Request failed (${error.status}).`,
  };
}

export function rethrowApiError(error: HttpErrorResponse) {
  return throwError(() => toApiError(error));
}
