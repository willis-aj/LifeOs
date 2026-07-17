import { Service, computed, signal } from '@angular/core';

const STORAGE_KEY = 'lifeos.currentPlayerId';

/** Holds which player is "active" for the whole app - the id is persisted
 * to localStorage so refreshing the page keeps you on the same player.
 * Every feature route reads the active player id from here rather than
 * threading it through route params. */
@Service()
export class PlayerContextService {
  private readonly playerIdSignal = signal<string | null>(this.readStoredPlayerId());
  private readonly playerNameSignal = signal<string | null>(null);

  readonly playerId = this.playerIdSignal.asReadonly();
  readonly playerName = this.playerNameSignal.asReadonly();
  readonly hasPlayer = computed(() => this.playerIdSignal() !== null);

  setPlayer(id: string, name: string): void {
    this.playerIdSignal.set(id);
    this.playerNameSignal.set(name);
    try {
      localStorage.setItem(STORAGE_KEY, id);
    } catch {
      // localStorage can throw in restrictive environments (private mode,
      // disabled storage) - the in-memory signal still works for this tab.
    }
  }

  clearPlayer(): void {
    this.playerIdSignal.set(null);
    this.playerNameSignal.set(null);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // see note above
    }
  }

  private readStoredPlayerId(): string | null {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch {
      return null;
    }
  }
}
