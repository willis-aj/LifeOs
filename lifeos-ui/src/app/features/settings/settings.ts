import { Component, OnInit, signal } from '@angular/core';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import { forkJoin } from 'rxjs';

import { CompanionService, CompanionSummary, CurrentCompanion } from '../../core/services/companion.service';
import { SeasonService, CurrentSeason } from '../../core/services/season.service';
import { InventoryService, InventoryItem } from '../../core/services/inventory.service';
import { RoutineService } from '../../core/services/routine.service';
import { PlayerService } from '../../core/services/player.service';
import { NotifyService } from '../../core/services/notify.service';
import { PlayerContextService } from '../../core/state/player-context.service';
import { PlayerDetail } from '../../core/models/player.model';
import { Routine } from '../../core/models/routine.model';

/** Player info, companion selection, current season, inventory, and
 * routines - the "everything else" corner of the app that doesn't belong
 * on Home/Day/Month/Backlog/Goals/Modes. */
@Component({
  selector: 'app-settings',
  imports: [
    MatButtonModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatTooltipModule,
  ],
  templateUrl: './settings.html',
  styleUrl: './settings.scss',
})
export class Settings implements OnInit {
  readonly loading = signal(true);
  readonly player = signal<PlayerDetail | null>(null);
  readonly companions = signal<CompanionSummary[]>([]);
  readonly currentCompanion = signal<CurrentCompanion | null>(null);
  readonly currentSeason = signal<CurrentSeason | null>(null);
  readonly inventory = signal<InventoryItem[]>([]);
  readonly routines = signal<Routine[]>([]);

  constructor(
    private readonly companionService: CompanionService,
    private readonly seasonService: SeasonService,
    private readonly inventoryService: InventoryService,
    private readonly routineService: RoutineService,
    private readonly playerService: PlayerService,
    private readonly notify: NotifyService,
    private readonly playerContext: PlayerContextService,
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
    forkJoin({
      player: this.playerService.getPlayer(playerId),
      companions: this.companionService.listCompanions(),
      currentCompanion: this.companionService.getCurrentCompanion(playerId),
      currentSeason: this.seasonService.getCurrentSeason(playerId),
      inventory: this.inventoryService.getInventory(playerId),
      routines: this.routineService.listRoutines(playerId),
    }).subscribe({
      next: (result) => {
        this.player.set(result.player);
        this.companions.set(result.companions);
        this.currentCompanion.set(result.currentCompanion);
        this.currentSeason.set(result.currentSeason);
        this.inventory.set(result.inventory);
        this.routines.set(result.routines);
        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        this.notify.error(err);
      },
    });
  }

  selectCompanion(companionId: string): void {
    const playerId = this.playerContext.playerId();
    if (!playerId) return;
    this.companionService.setCompanion(playerId, companionId).subscribe({
      next: (result) => {
        this.currentCompanion.set(result);
        this.notify.success('Companion updated.');
      },
      error: (err) => this.notify.error(err),
    });
  }
}
