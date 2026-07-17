import { Service, effect, signal } from '@angular/core';

export type ThemeMode = 'light' | 'dark';

const STORAGE_KEY = 'lifeos.theme';

/** Toggles the `dark-theme` class on <html> (see styles.scss for the
 * matching Material theme override) and remembers the user's choice,
 * defaulting to their OS-level preference on first visit. */
@Service()
export class ThemeService {
  private readonly modeSignal = signal<ThemeMode>(this.readInitialMode());
  readonly mode = this.modeSignal.asReadonly();

  constructor() {
    effect(() => {
      const mode = this.modeSignal();
      document.documentElement.classList.toggle('dark-theme', mode === 'dark');
      try {
        localStorage.setItem(STORAGE_KEY, mode);
      } catch {
        // ignore - theme just won't persist across reloads in this case
      }
    });
  }

  toggle(): void {
    this.modeSignal.set(this.modeSignal() === 'dark' ? 'light' : 'dark');
  }

  setMode(mode: ThemeMode): void {
    this.modeSignal.set(mode);
  }

  private readInitialMode(): ThemeMode {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === 'light' || stored === 'dark') {
        return stored;
      }
    } catch {
      // ignore and fall through to system preference
    }
    const prefersDark = typeof window !== 'undefined'
      && window.matchMedia
      && window.matchMedia('(prefers-color-scheme: dark)').matches;
    return prefersDark ? 'dark' : 'light';
  }
}
