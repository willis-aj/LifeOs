import { Component, OnInit, signal } from '@angular/core';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';

import { GoalService } from '../../core/services/goal.service';
import { NotifyService } from '../../core/services/notify.service';
import { PlayerContextService } from '../../core/state/player-context.service';
import { GoalProgress } from '../../core/models/goal.model';
import { GoalFormDialog, GoalFormDialogData } from '../../shared/goal-form-dialog/goal-form-dialog';
import { ConfirmDialog, ConfirmDialogData } from '../../shared/confirm-dialog/confirm-dialog';

/** Goal list/add/edit/delete - mirrors the CLI's "edit goals" menu. Each
 * goal shows its level (derived from milestones reached), a progress bar
 * toward the next milestone, and per-goal edit/delete actions. */
@Component({
  selector: 'app-goals',
  imports: [
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
  ],
  templateUrl: './goals.html',
  styleUrl: './goals.scss',
})
export class Goals implements OnInit {
  readonly loading = signal(true);
  readonly goals = signal<GoalProgress[]>([]);

  constructor(
    private readonly goalService: GoalService,
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
    this.goalService.listGoals(playerId).subscribe({
      next: (goals) => {
        this.goals.set(goals);
        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        this.notify.error(err);
      },
    });
  }

  progressPercent(goal: GoalProgress): number {
    if (goal.next_milestone == null) return 100;
    const previousMilestone = goal.milestones_reached.length
      ? goal.milestones_reached[goal.milestones_reached.length - 1]
      : 0;
    const span = goal.next_milestone - previousMilestone;
    if (span <= 0) return 100;
    return Math.min(100, Math.max(0, ((goal.xp - previousMilestone) / span) * 100));
  }

  openAdd(): void {
    const ref = this.dialog.open<GoalFormDialog, GoalFormDialogData>(GoalFormDialog, {
      width: '440px',
      data: {},
    });
    ref.afterClosed().subscribe((request) => {
      if (!request) return;
      const playerId = this.playerContext.playerId();
      if (!playerId) return;
      this.goalService.addGoal(playerId, request).subscribe({
        next: () => {
          this.notify.success('Goal added.');
          this.reload();
        },
        error: (err) => this.notify.error(err),
      });
    });
  }

  openEdit(goal: GoalProgress): void {
    const ref = this.dialog.open<GoalFormDialog, GoalFormDialogData>(GoalFormDialog, {
      width: '440px',
      data: { goal },
    });
    ref.afterClosed().subscribe((request) => {
      if (!request) return;
      const playerId = this.playerContext.playerId();
      if (!playerId) return;
      this.goalService.editGoal(playerId, goal.id, request).subscribe({
        next: () => {
          this.notify.success('Goal updated.');
          this.reload();
        },
        error: (err) => this.notify.error(err),
      });
    });
  }

  openDelete(goal: GoalProgress): void {
    const data: ConfirmDialogData = {
      title: 'Delete goal',
      message: `Delete "${goal.name}"? This cannot be undone.`,
      confirmLabel: 'Delete',
      danger: true,
    };
    const ref = this.dialog.open<ConfirmDialog, ConfirmDialogData, boolean>(ConfirmDialog, {
      width: '380px',
      data,
    });
    ref.afterClosed().subscribe((confirmed) => {
      if (!confirmed) return;
      const playerId = this.playerContext.playerId();
      if (!playerId) return;
      this.goalService.deleteGoal(playerId, goal.id).subscribe({
        next: () => {
          this.notify.success('Goal deleted.');
          this.reload();
        },
        error: (err) => this.notify.error(err),
      });
    });
  }
}
