import { Component, OnInit, signal } from '@angular/core';
import { Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { ScheduleService } from '../../core/services/schedule.service';
import { TaskService } from '../../core/services/task.service';
import { EventService } from '../../core/services/event.service';
import { NotifyService } from '../../core/services/notify.service';
import { PlayerContextService } from '../../core/state/player-context.service';
import { BacklogDayEntry, BacklogView as BacklogViewModel, LifeTask } from '../../core/models/task.model';
import { TaskItem } from '../../shared/task-item/task-item';
import { EditTaskDialog } from '../../shared/edit-task-dialog/edit-task-dialog';
import {
  ScheduledEventDialog,
  ScheduledEventDialogData,
} from '../../shared/scheduled-event-dialog/scheduled-event-dialog';

/** Tasks pushed forward today (skip, dependency push, hour drift,
 * end-of-day rollover), what's already lined up for tomorrow, and what's
 * coming later this week - mirrors the CLI's [b]acklog view. Pull-forward
 * is available everywhere here since bringing something into today early
 * is exactly what this view is for. */
@Component({
  selector: 'app-backlog-view',
  imports: [MatIconModule, MatProgressSpinnerModule, TaskItem],
  templateUrl: './backlog-view.html',
  styleUrl: './backlog-view.scss',
})
export class BacklogView implements OnInit {
  readonly loading = signal(true);
  readonly backlog = signal<BacklogViewModel | null>(null);

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
    if (!playerId) return;
    this.loading.set(true);
    this.scheduleService.getBacklog(playerId).subscribe({
      next: (backlog) => {
        this.backlog.set(backlog);
        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        this.notify.error(err);
      },
    });
  }

  trackByDate(_: number, entry: BacklogDayEntry): string {
    return entry.date;
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

  onPullForward(task: LifeTask): void {
    const playerId = this.playerContext.playerId();
    if (!playerId) return;
    this.taskService.pullTaskForward(playerId, task.id).subscribe({
      next: () => {
        this.notify.success('Task pulled forward into the current hour.');
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
