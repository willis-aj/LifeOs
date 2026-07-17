import { Component, Inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { GoalService } from '../../core/services/goal.service';
import { NotifyService } from '../../core/services/notify.service';
import { EditTaskRequest } from '../../core/services/task.service';
import { GoalProgress } from '../../core/models/goal.model';
import { LifeTask } from '../../core/models/task.model';

export interface EditTaskDialogData {
  task: LifeTask;
  playerId: string;
}

/** Form for editing a task's label, duration, goal, XP, and hour. Closes
 * with an EditTaskRequest containing only the fields the user actually
 * changed, or undefined if cancelled. */
@Component({
  selector: 'app-edit-task-dialog',
  imports: [FormsModule, MatDialogModule, MatFormFieldModule, MatInputModule, MatSelectModule, MatButtonModule],
  templateUrl: './edit-task-dialog.html',
  styleUrl: './edit-task-dialog.scss',
})
export class EditTaskDialog implements OnInit {
  readonly goals = signal<GoalProgress[]>([]);

  label: string;
  durationMinutes: number;
  goalId: string;
  xp: number;
  hour: number;

  constructor(
    private readonly dialogRef: MatDialogRef<EditTaskDialog, EditTaskRequest>,
    private readonly goalService: GoalService,
    private readonly notify: NotifyService,
    @Inject(MAT_DIALOG_DATA) public data: EditTaskDialogData,
  ) {
    this.label = data.task.label;
    this.durationMinutes = data.task.duration_minutes;
    this.goalId = data.task.goal;
    this.xp = data.task.xp;
    this.hour = data.task.scheduled_hour;
  }

  ngOnInit(): void {
    this.goalService.listGoals(this.data.playerId).subscribe({
      next: (goals) => this.goals.set(goals),
      error: (err) => this.notify.error(err),
    });
  }

  submit(): void {
    if (!this.label.trim() || this.durationMinutes <= 0) {
      return;
    }
    const changes: EditTaskRequest = {
      label: this.label.trim(),
      duration_minutes: this.durationMinutes,
      goal_id: this.goalId,
      xp: this.xp,
      hour: this.hour,
    };
    this.dialogRef.close(changes);
  }

  cancel(): void {
    this.dialogRef.close();
  }
}
