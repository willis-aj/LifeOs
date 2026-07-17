import { Component, OnInit, computed, signal } from '@angular/core';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { ScheduleService, HomeView } from '../../core/services/schedule.service';
import { TaskService } from '../../core/services/task.service';
import { EventService } from '../../core/services/event.service';
import { NotifyService } from '../../core/services/notify.service';
import { PlayerContextService } from '../../core/state/player-context.service';
import { LifeTask } from '../../core/models/task.model';
import { TaskItem } from '../../shared/task-item/task-item';
import { EditTaskDialog } from '../../shared/edit-task-dialog/edit-task-dialog';
import {
  ScheduledEventDialog,
  ScheduledEventDialogData,
} from '../../shared/scheduled-event-dialog/scheduled-event-dialog';

/** The main home dashboard: level/XP/streak/mode/boss-fights/companion
 * plus the current hour's tasks - the same thing the CLI shows on every
 * check-in tick. */
@Component({
  selector: 'app-home',
  imports: [
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatIconModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    TaskItem,
  ],
  templateUrl: './home.html',
  styleUrl: './home.scss',
})
export class Home implements OnInit {
  readonly loading = signal(true);
  readonly view = signal<HomeView | null>(null);
  readonly xpProgressPercent = computed(() => {
    const v = this.view();
    if (!v || v.state.xp_to_next === 0) {
      return 0;
    }
    return Math.min(100, Math.round((v.state.xp_into_level / v.state.xp_to_next) * 100));
  });

  constructor(
    private readonly scheduleService: ScheduleService,
    private readonly taskService: TaskService,
    private readonly eventService: EventService,
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
    if (!playerId) {
      return;
    }
    this.loading.set(true);
    this.scheduleService.getHome(playerId).subscribe({
      next: (view) => {
        this.view.set(view);
        this.loading.set(false);
        this.reportCheckin(view);
      },
      error: (err) => {
        this.loading.set(false);
        this.notify.error(err);
      },
    });
  }

  private reportCheckin(view: HomeView): void {
    const checkin = view.checkin;
    if (!checkin) {
      return;
    }
    if (checkin.rolled_over) {
      const dayWord = checkin.days_advanced === 1 ? 'day' : 'days';
      this.notify.success(
        `New day detected (${checkin.days_advanced} ${dayWord} passed) - rolled ${checkin.carried_count} unfinished task(s) forward.`,
      );
    }
    if (checkin.overdue_moved_count > 0) {
      this.notify.success('Unfinished tasks detected - moved to the current hour.');
    }
    for (const fix of checkin.dependency_fixes) {
      this.notify.success(
        `Prerequisite missing - added ${fix.prerequisite.toLowerCase()} before ${fix.dependent.toLowerCase()}.`,
      );
    }
  }

  onComplete(task: LifeTask): void {
    const playerId = this.playerContext.playerId();
    if (!playerId) return;
    this.taskService.completeTask(playerId, task.id).subscribe({
      next: (result) => {
        const xp = result['xp_gained'];
        this.notify.success(typeof xp === 'number' ? `+${xp} XP!` : 'Task completed!');
        if (result['scheduling_task_completed']) {
          this.openScheduledEventDialog(task, playerId);
        } else {
          this.reload();
        }
      },
      error: (err) => this.notify.error(err),
    });
  }

  onSkip(task: LifeTask): void {
    const playerId = this.playerContext.playerId();
    if (!playerId) return;
    this.taskService.skipTask(playerId, task.id).subscribe({
      next: (result) => {
        this.notify.success(result.message ?? 'Skipped.');
        this.reload();
      },
      error: (err) => this.notify.error(err),
    });
  }

  onDelete(task: LifeTask): void {
    const playerId = this.playerContext.playerId();
    if (!playerId) return;
    this.taskService.deleteTask(playerId, task.id).subscribe({
      next: () => {
        this.notify.success('Task deleted.');
        this.reload();
      },
      error: (err) => this.notify.error(err),
    });
  }

  onEdit(task: LifeTask): void {
    const playerId = this.playerContext.playerId();
    if (!playerId) return;
    const ref = this.dialog.open(EditTaskDialog, { width: '420px', data: { task, playerId } });
    ref.afterClosed().subscribe((changes) => {
      if (!changes) return;
      this.taskService.editTask(playerId, task.id, changes).subscribe({
        next: () => {
          this.notify.success('Task updated.');
          this.reload();
        },
        error: (err) => this.notify.error(err),
      });
    });
  }

  private openScheduledEventDialog(completedTask: LifeTask, playerId: string): void {
    const data: ScheduledEventDialogData = { scheduledTaskLabel: completedTask.label, playerId };
    const ref = this.dialog.open(ScheduledEventDialog, { width: '440px', data });
    ref.afterClosed().subscribe((request) => {
      if (!request) {
        this.reload();
        return;
      }
      this.eventService.createScheduledEvent(playerId, request).subscribe({
        next: () => {
          this.notify.success('Event created and scheduled.');
          this.reload();
        },
        error: (err) => {
          this.notify.error(err);
          this.reload();
        },
      });
    });
  }
}
