import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { provideNativeDateAdapter } from '@angular/material/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideRouter } from '@angular/router';

import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideHttpClient(),
    provideAnimationsAsync(),
    // MatDatepicker's calendar overlay is portaled near the app root and
    // resolves DateAdapter from the root injector - importing
    // MatNativeDateModule into a dialog's own `imports` array isn't
    // enough (NG0201: no provider for DateAdapter). This provides it app-wide.
    provideNativeDateAdapter(),
  ]
};
