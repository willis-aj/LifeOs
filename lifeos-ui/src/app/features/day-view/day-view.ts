import { Component, OnInit, signal } from '@angular/core';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { ScheduleService } from '../../core/services/schedule.service';
import { TaskService } from '../../core/services/task.service';
import { EventService } from '../../core/services/event.service';
import { NotifyService } from '../../core/services/notify.service';
import { PlayerContextService } from '../../core/state/player-context.service';
import { HourGroup, LifeTask } from '../../core/models/task.model';
import { formatHour } from '../../core/utils/format-hour';
import { TaskItem } from '../../shared/task-item/task-item';
import { AddTaskDialog, AddTaskDialogData } from '../../shared/add-task-dialog/add-task-dialog';
import { EditTaskDialog } from '../../shared/edit-task-dialog/edit-task-dialog';
import {
  ScheduledEventDialog,
  ScheduledEventDialogData,
} from '../../shared/scheduled-event-dialog/scheduled-event-dialog';
import {
  CompleteTaskDialog,
  CompleteTaskDialogData,
  CompleteTaskDialogResult,
} from '../../shared/complete-task-dialog/complete-task-dialog';

/** Every scheduled hour today, grouped, with complete/skip/edit/delete/
 * pull-forward actions on each task - mirrors the CLI's [d]ay view, but
 * fully interactive instead of read-only. */
@Component({
  selector: 'app-day-view',
  imports: [MatButtonModule, MatIconModule, MatProgressSpinnerModule, TaskItem],
  templateUrl: './day-view.html',
  styleUrl: './day-view.scss',
})
export class DayView implements OnInit {
  readonly loading = signal(true);
  readonly groups = signal<HourGroup[]>([]);

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

  readonly formatHour = formatHour;

  reload(): void {
    const playerId = this.playerContext.playerId();
    if (!playerId) return;
    this.loading.set(true);
    this.scheduleService.getDay(playerId).subscribe({
      next: (groups) => {
        this.groups.set(groups);
        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        this.notify.error(err);
      },
    });
  }

  openAddTaskDialog(): void {
    const playerId = this.playerContext.playerId();
    if (!playerId) return;
    const data: AddTaskDialogData = { playerId };
    const ref = this.dialog.open(AddTaskDialog, { width: '400px', data });
    ref.afterClosed().subscribe((request) => {
      if (!request) return;
      this.taskService.addManualTask(playerId, request).subscribe({
        next: () => {
          this.notify.success('Task added.');
          this.reload();
        },
        error: (err) => this.notify.error(err),
      });
    });
  }

  onComplete(task: LifeTask): void {
    const playerId = this.playerContext.playerId();
    if (!playerId) return;
    const data: CompleteTaskDialogData = { task, playerId };
    const ref = this.dialog.open<CompleteTaskDialog, CompleteTaskDialogData, CompleteTaskDialogResult>(
      CompleteTaskDialog,
      { width: '480px', data },
    );
    ref.afterClosed().subscribe((completion) => {
      if (!completion) return;
      this.taskService.completeTask(playerId, task.id, completion).subscribe({
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
