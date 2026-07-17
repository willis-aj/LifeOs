import { Component, OnInit, signal } from '@angular/core';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { PlayerService } from '../../core/services/player.service';
import { NotifyService } from '../../core/services/notify.service';
import { PlayerContextService } from '../../core/state/player-context.service';
import { PlayerSummary } from '../../core/models/player.model';
import { PlayerCreate } from '../player-create/player-create';
import { PlayerDelete } from '../player-delete/player-delete';

/** The player-selection screen: list existing players, create a new one,
 * delete one, or pick one to load and jump to the home dashboard. Mirrors
 * the CLI's "Select player" menu, including auto-prompting to create a
 * player the moment none exist yet. */
@Component({
  selector: 'app-player-select',
  imports: [MatButtonModule, MatCardModule, MatIconModule, MatListModule, MatProgressSpinnerModule],
  templateUrl: './player-select.html',
  styleUrl: './player-select.scss',
})
export class PlayerSelect implements OnInit {
  readonly players = signal<PlayerSummary[]>([]);
  readonly loading = signal(true);

  constructor(
    private readonly playerService: PlayerService,
    private readonly playerContext: PlayerContextService,
    private readonly notify: NotifyService,
    private readonly dialog: MatDialog,
    private readonly router: Router,
  ) {}

  ngOnInit(): void {
    this.reload(true);
  }

  reload(promptIfEmpty = false): void {
    this.loading.set(true);
    this.playerService.listPlayers().subscribe({
      next: (players) => {
        this.players.set(players);
        this.loading.set(false);
        if (promptIfEmpty && players.length === 0) {
          this.openCreateDialog();
        }
      },
      error: (err) => {
        this.loading.set(false);
        this.notify.error(err);
      },
    });
  }

  openCreateDialog(): void {
    const ref = this.dialog.open(PlayerCreate, { width: '360px' });
    ref.afterClosed().subscribe((name) => {
      if (!name) {
        return;
      }
      this.playerService.createPlayer(name).subscribe({
        next: (detail) => {
          this.notify.success(`Welcome, ${detail.name}!`);
          this.selectPlayer(detail.id, detail.name);
        },
        error: (err) => this.notify.error(err),
      });
    });
  }

  openDeleteDialog(player: PlayerSummary, event: Event): void {
    event.stopPropagation();
    const ref = this.dialog.open(PlayerDelete, { width: '400px', data: { playerName: player.name } });
    ref.afterClosed().subscribe((confirmed) => {
      if (!confirmed) {
        return;
      }
      this.playerService.deletePlayer(player.id).subscribe({
        next: () => {
          this.notify.success(`Deleted ${player.name}.`);
          this.reload(true);
        },
        error: (err) => this.notify.error(err),
      });
    });
  }

  selectPlayer(id: string, name: string): void {
    this.playerContext.setPlayer(id, name);
    this.router.navigate(['/home']);
  }
}
