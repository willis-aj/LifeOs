import { Component, OnInit, input, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';

import { ScheduleService } from '../../core/services/schedule.service';
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

/** A focused view of a single hour's tasks (defaults to the current hour)
 * with full complete/skip/edit/delete actions. Self-contained so it can be
 * embedded anywhere (dashboards, widgets) or used standalone - unlike
 * day-view it doesn't offer pull-forward, since there's nothing "later
 * today" in scope when you're only looking at one hour. */
@Component({
  selector: 'app-hour-view',
  imports: [MatButtonModule, MatIconModule, MatProgressSpinnerModule, MatTooltipModule, TaskItem],
  templateUrl: './hour-view.html',
  styleUrl: './hour-view.scss',
})
export class HourView implements OnInit {
  /** Which hour to show (0-23). Omit to show the current hour. */
  readonly hour = input<number | undefined>(undefined);

  readonly loading = signal(true);
  readonly resolvedHour = signal<number>(new Date().getHours());
  readonly tasks = signal<LifeTask[]>([]);

  constructor(
    private readonly scheduleService: ScheduleService,
    private readonly taskService: TaskService,
    private readonly eventService: EventService,
    private readonly notify: NotifyService,
    private readonly playerContext: PlayerContextService,
    private readonly dialog: MatDialog,
  ) {}

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    const playerId = this.playerContext.playerId();
    if (!playerId) return;
    this.loading.set(true);
    this.scheduleService.getHour(playerId, this.hour()).subscribe({
      next: (view) => {
        this.resolvedHour.set(view.hour);
        this.tasks.set(view.tasks);
        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        this.notify.error(err);
      },
    });
  }

  formatHour(hour: number): string {
    const period = hour < 12 ? 'AM' : 'PM';
    let display = hour % 12;
    if (display === 0) display = 12;
    return `${display}:00 ${period}`;
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
