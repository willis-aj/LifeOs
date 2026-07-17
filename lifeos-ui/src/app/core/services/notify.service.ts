import { Service, inject } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';

import { ApiError } from './api-error.util';

/** Thin wrapper around MatSnackBar so every component reports errors and
 * confirmations the same way. */
@Service()
export class NotifyService {
  private readonly snackBar = inject(MatSnackBar);

  error(error: ApiError | string): void {
    const message = typeof error === 'string' ? error : error.message;
    this.snackBar.open(message, 'Dismiss', { duration: 6000, panelClass: 'lifeos-snack-error' });
  }

  success(message: string): void {
    this.snackBar.open(message, undefined, { duration: 3000, panelClass: 'lifeos-snack-success' });
  }
}
