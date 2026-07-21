import { Component, OnInit, inject, input, output, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

import { SelfCareService } from '../../core/services/self-care.service';
import { ModeService } from '../../core/services/mode.service';
import { NotifyService } from '../../core/services/notify.service';
import { SelfCareStatus } from '../../core/models/self-care.model';

/** Today's self-care nudges from the Self-Care Agent, plus a soft
 * suggestion to switch to Comfort Mode when its overwhelm signals fire.
 * Self-contained (fetches its own status) so it can be dropped anywhere a
 * playerId is available; emits `comfortModeToggled` so a host view (e.g.
 * Home) knows to reload its own task list after the mode actually changes.
 * Renders nothing when there's nothing to say - quiet by default. For the
 * conversational counterpart, see shared/chat-panel. */
@Component({
  selector: 'app-self-care-panel',
  imports: [MatButtonModule, MatIconModule],
  templateUrl: './self-care-panel.html',
  styleUrl: './self-care-panel.scss',
})
export class SelfCarePanel implements OnInit {
  readonly playerId = input.required<string>();
  readonly comfortModeToggled = output<void>();

  private readonly selfCareService = inject(SelfCareService);
  private readonly modeService = inject(ModeService);
  private readonly notify = inject(NotifyService);

  readonly status = signal<SelfCareStatus | null>(null);
  readonly switching = signal(false);

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    this.selfCareService.getStatus(this.playerId()).subscribe({
      next: (status) => this.status.set(status),
      error: () => {
        // Quiet failure - the self-care panel is a bonus layer over the
        // normal task list, never a blocker.
      },
    });
  }

  switchToComfortMode(): void {
    this.switching.set(true);
    this.modeService.toggleComfortMode(this.playerId()).subscribe({
      next: () => {
        this.switching.set(false);
        this.notify.success('Switched to Comfort Mode.');
        this.comfortModeToggled.emit();
        this.reload();
      },
      error: (err) => {
        this.switching.set(false);
        this.notify.error(err);
      },
    });
  }
}
