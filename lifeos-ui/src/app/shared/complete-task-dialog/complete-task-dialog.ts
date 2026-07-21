import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { GoalProgress } from '../../core/models/goal.model';
import { DIFFICULTY_LABELS, LifeTask, TaskDifficulty } from '../../core/models/task.model';
import { GoalService } from '../../core/services/goal.service';
import { EventService } from '../../core/services/event.service';
import { RoutineService } from '../../core/services/routine.service';
import { NotifyService } from '../../core/services/notify.service';

export interface CompleteTaskDialogData {
  task: LifeTask;
  playerId: string;
}

export interface CompleteTaskDialogResult {
  difficulty?: string;
  notes?: string;
}

type Recurrence = 'none' | 'daily' | 'weekly' | 'monthly';

/** Shown when a task is completed: an optional difficulty rating, a notes
 * field (pre-filled from the task/routine's note template if it has one),
 * and a small "create new event or routine" form for capturing a
 * follow-up on the spot. The mini-form creates its own event/routine
 * immediately via the backend when "Add to LifeOS" is pressed; Save only
 * needs to carry difficulty/notes back to the caller, which completes the
 * task with them. Closing with no result (Cancel) leaves the task
 * incomplete. */
@Component({
  selector: 'app-complete-task-dialog',
  imports: [FormsModule, MatDialogModule, MatButtonModule, MatFormFieldModule, MatInputModule, MatSelectModule],
  templateUrl: './complete-task-dialog.html',
  styleUrl: './complete-task-dialog.scss',
})
export class CompleteTaskDialog implements OnInit {
  private readonly goalService = inject(GoalService);
  private readonly eventService = inject(EventService);
  private readonly routineService = inject(RoutineService);
  private readonly notify = inject(NotifyService);
  private readonly dialogRef = inject<MatDialogRef<CompleteTaskDialog, CompleteTaskDialogResult>>(MatDialogRef);
  readonly data = inject<CompleteTaskDialogData>(MAT_DIALOG_DATA);

  readonly difficultyLabels = DIFFICULTY_LABELS;
  readonly difficultyOptions = Object.keys(DIFFICULTY_LABELS) as TaskDifficulty[];
  readonly goals = signal<GoalProgress[]>([]);
  readonly adding = signal(false);
  readonly lastAdded = signal<string | null>(null);

  difficulty: TaskDifficulty | '' = '';
  notes = this.data.task.note_template ?? '';

  newItemName = '';
  newItemDuration: number | null = null;
  newItemGoalId = '';
  newItemRecurrence: Recurrence = 'none';

  ngOnInit(): void {
    this.goalService.listGoals(this.data.playerId).subscribe({
      next: (goals) => this.goals.set(goals),
      error: (err) => this.notify.error(err),
    });
  }

  addToLifeOs(): void {
    const name = this.newItemName.trim();
    if (!name) return;

    this.adding.set(true);
    this.lastAdded.set(null);
    const goalId = this.newItemGoalId || undefined;

    if (this.newItemRecurrence === 'none') {
      const today = new Date().toISOString().slice(0, 10);
      this.eventService
        .createScheduledEvent(this.data.playerId, {
          date: today,
          label: name,
          duration_minutes: this.newItemDuration ?? 60,
          goal_id: goalId,
        })
        .subscribe({
          next: () => this.onAdded(name),
          error: (err) => {
            this.adding.set(false);
            this.notify.error(err);
          },
        });
    } else {
      this.routineService
        .addRoutine(this.data.playerId, {
          label: name,
          duration_minutes: this.newItemDuration ?? 30,
          goal_id: goalId,
          frequency: this.newItemRecurrence,
        })
        .subscribe({
          next: () => this.onAdded(name),
          error: (err) => {
            this.adding.set(false);
            this.notify.error(err);
          },
        });
    }
  }

  private onAdded(name: string): void {
    this.adding.set(false);
    this.lastAdded.set(name);
    this.notify.success(`"${name}" added to LifeOS.`);
    this.newItemName = '';
    this.newItemDuration = null;
  }

  save(): void {
    const result: CompleteTaskDialogResult = {
      difficulty: this.difficulty || undefined,
      notes: this.notes.trim() || undefined,
    };
    this.dialogRef.close(result);
  }

  cancel(): void {
    this.dialogRef.close();
  }
}
