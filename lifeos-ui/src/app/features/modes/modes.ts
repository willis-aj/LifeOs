import { Component, OnInit, signal } from '@angular/core';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatDialog } from '@angular/material/dialog';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSlideToggleModule, MatSlideToggleChange } from '@angular/material/slide-toggle';

import { ModeService, ModeInfo } from '../../core/services/mode.service';
import { NotifyService } from '../../core/services/notify.service';
import { PlayerContextService } from '../../core/state/player-context.service';
import { EnergyMode } from '../../core/models/player.model';
import { ConfirmDialog, ConfirmDialogData } from '../../shared/confirm-dialog/confirm-dialog';

const ENERGY_MODE_LABELS: Record<EnergyMode, string> = {
  low: 'Low energy',
  normal: 'Normal',
  high: 'High energy',
};

/** Energy mode, Chaos Mode, and Comfort Mode management, plus player reset -
 * mirrors the CLI's mode-switching menu. */
@Component({
  selector: 'app-modes',
  imports: [
    MatButtonModule,
    MatButtonToggleModule,
    MatSlideToggleModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './modes.html',
  styleUrl: './modes.scss',
})
export class Modes implements OnInit {
  readonly loading = signal(true);
  readonly mode = signal<ModeInfo | null>(null);
  readonly energyModeLabels = ENERGY_MODE_LABELS;

  constructor(
    private readonly modeService: ModeService,
    private readonly notify: NotifyService,
    private readonly playerContext: PlayerContextService,
    private readonly dialog: MatDialog,
    private readonly router: Router,
  ) {}

  ngOnInit(): void {
    if (!this.playerContext.hasPlayer()) {
      this.router.navigate(['/players']);
      return;
    }
    this.reload();
  }

  reload(): void {
    const playerId = this.playerContext.playerId();
    if (!playerId) return;
    this.loading.set(true);
    this.modeService.getMode(playerId).subscribe({
      next: (mode) => {
        this.mode.set(mode);
        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        this.notify.error(err);
      },
    });
  }

  setEnergyMode(mode: EnergyMode): void {
    const playerId = this.playerContext.playerId();
    if (!playerId) return;
    this.modeService.setEnergyMode(playerId, mode).subscribe({
      next: () => {
        this.notify.success(`Energy mode set to ${ENERGY_MODE_LABELS[mode]}.`);
        this.reload();
      },
      error: (err) => this.notify.error(err),
    });
  }

  toggleChaos(event: MatSlideToggleChange): void {
    const playerId = this.playerContext.playerId();
    if (!playerId) {
      event.source.checked = !event.checked;
      return;
    }
    this.modeService.toggleChaosMode(playerId).subscribe({
      next: (result) => {
        this.notify.success(result.chaos_mode ? 'Chaos Mode enabled.' : 'Chaos Mode disabled.');
        this.reload();
      },
      error: (err) => {
        event.source.checked = !event.checked;
        this.notify.error(err);
      },
    });
  }

  toggleComfort(event: MatSlideToggleChange): void {
    const playerId = this.playerContext.playerId();
    if (!playerId) {
      event.source.checked = !event.checked;
      return;
    }
    this.modeService.toggleComfortMode(playerId).subscribe({
      next: (result) => {
        this.notify.success(result.comfort_mode ? 'Comfort Mode enabled.' : 'Comfort Mode disabled.');
        this.reload();
      },
      error: (err) => {
        event.source.checked = !event.checked;
        this.notify.error(err);
      },
    });
  }

  openReset(): void {
    const data: ConfirmDialogData = {
      title: 'Reset player',
      message: 'This resets XP, level, streaks, and progress back to the start. This cannot be undone.',
      confirmLabel: 'Reset',
      danger: true,
    };
    const ref = this.dialog.open<ConfirmDialog, ConfirmDialogData, boolean>(ConfirmDialog, {
      width: '420px',
      data,
    });
    ref.afterClosed().subscribe((confirmed) => {
      if (!confirmed) return;
      const playerId = this.playerContext.playerId();
      if (!playerId) return;
      this.modeService.resetPlayer(playerId).subscribe({
        next: () => {
          this.notify.success('Player reset.');
          this.reload();
        },
        error: (err) => this.notify.error(err),
      });
    });
  }
}
