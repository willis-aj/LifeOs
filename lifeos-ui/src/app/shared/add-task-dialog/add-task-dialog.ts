import { Component, Inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { AddManualTaskRequest } from '../../core/services/task.service';
import { GoalService } from '../../core/services/goal.service';
import { GoalProgress } from '../../core/models/goal.model';
import { NotifyService } from '../../core/services/notify.service';

export interface AddTaskDialogData {
  playerId: string;
  defaultHour?: number;
}

/** Form for adding a brand-new manual task - name, duration, goal, and an
 * optional hour (defaults to "now" on the server if omitted). Closes with
 * an AddManualTaskRequest, or undefined if cancelled. */
@Component({
  selector: 'app-add-task-dialog',
  imports: [FormsModule, MatDialogModule, MatFormFieldModule, MatInputModule, MatSelectModule, MatButtonModule],
  templateUrl: './add-task-dialog.html',
  styleUrl: './add-task-dialog.scss',
})
export class AddTaskDialog implements OnInit {
  readonly goals = signal<GoalProgress[]>([]);
  readonly hours = Array.from({ length: 24 }, (_, h) => h);

  label = '';
  durationMinutes = 30;
  goalId = '';
  hour: number | null = null;

  constructor(
    private readonly dialogRef: MatDialogRef<AddTaskDialog, AddManualTaskRequest>,
    private readonly goalService: GoalService,
    private readonly notify: NotifyService,
    @Inject(MAT_DIALOG_DATA) public data: AddTaskDialogData,
  ) {
    this.hour = data.defaultHour ?? null;
  }

  ngOnInit(): void {
    this.goalService.listGoals(this.data.playerId).subscribe({
      next: (goals) => {
        this.goals.set(goals);
        if (goals.length > 0) {
          this.goalId = goals[0].id;
        }
      },
      error: (err) => this.notify.error(err),
    });
  }

  formatHour(hour: number): string {
    const period = hour < 12 ? 'AM' : 'PM';
    let display = hour % 12;
    if (display === 0) display = 12;
    return `${display}:00 ${period}`;
  }

  submit(): void {
    if (!this.label.trim() || this.durationMinutes <= 0) {
      return;
    }
    const request: AddManualTaskRequest = {
      label: this.label.trim(),
      duration_minutes: this.durationMinutes,
      goal_id: this.goalId || undefined,
      hour: this.hour ?? undefined,
    };
    this.dialogRef.close(request);
  }

  cancel(): void {
    this.dialogRef.close();
  }
}
