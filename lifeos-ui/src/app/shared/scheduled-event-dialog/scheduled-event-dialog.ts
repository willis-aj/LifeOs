import { Component, Inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatNativeDateModule } from '@angular/material/core';
import { MatSelectModule } from '@angular/material/select';

import { CreateScheduledEventRequest } from '../../core/services/event.service';
import { GoalService } from '../../core/services/goal.service';
import { GoalProgress } from '../../core/models/goal.model';
import { NotifyService } from '../../core/services/notify.service';
import { formatHour } from '../../core/utils/format-hour';

export interface ScheduledEventDialogData {
  scheduledTaskLabel: string;
  playerId: string;
}

/** After completing a scheduling-type task ("Schedule dinner with
 * friends", "Schedule raid", etc.), offers to create the actual one-off
 * event on a chosen date/time/duration. Closes with a
 * CreateScheduledEventRequest, or undefined if the user chooses "Not now". */
@Component({
  selector: 'app-scheduled-event-dialog',
  imports: [
    FormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatCheckboxModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatButtonModule,
  ],
  templateUrl: './scheduled-event-dialog.html',
  styleUrl: './scheduled-event-dialog.scss',
})
export class ScheduledEventDialog implements OnInit {
  readonly goals = signal<GoalProgress[]>([]);
  readonly hours = Array.from({ length: 24 }, (_, h) => h);

  label = '';
  date: Date = new Date();
  hour = 9;
  durationMinutes = 60;
  goalId = '';
  boss = false;

  constructor(
    private readonly dialogRef: MatDialogRef<ScheduledEventDialog, CreateScheduledEventRequest>,
    private readonly goalService: GoalService,
    private readonly notify: NotifyService,
    @Inject(MAT_DIALOG_DATA) public data: ScheduledEventDialogData,
  ) {
    this.label = data.scheduledTaskLabel;
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

  readonly formatHour = formatHour;

  create(): void {
    if (!this.date || this.durationMinutes <= 0) {
      return;
    }
    const iso = this.date.toISOString().slice(0, 10);
    const request: CreateScheduledEventRequest = {
      date: iso,
      label: this.label.trim() || undefined,
      hour: this.hour,
      duration_minutes: this.durationMinutes,
      goal_id: this.goalId || undefined,
      boss: this.boss,
    };
    this.dialogRef.close(request);
  }

  skip(): void {
    this.dialogRef.close();
  }
}
