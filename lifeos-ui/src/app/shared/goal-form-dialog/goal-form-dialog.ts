import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

import { AddGoalRequest, EditGoalRequest, GoalProgress } from '../../core/models/goal.model';

export interface GoalFormDialogData {
  /** Present when editing an existing goal; absent when adding a new one. */
  goal?: GoalProgress;
}

/** Shared add/edit form for goals. Closes with an AddGoalRequest when
 * data.goal is absent, or an EditGoalRequest when editing. Milestones are
 * entered as a comma-separated list of XP thresholds, mirroring the CLI's
 * plain-text milestone prompt. */
@Component({
  selector: 'app-goal-form-dialog',
  imports: [ReactiveFormsModule, MatDialogModule, MatButtonModule, MatFormFieldModule, MatInputModule],
  templateUrl: './goal-form-dialog.html',
  styleUrl: './goal-form-dialog.scss',
})
export class GoalFormDialog {
  private readonly fb = inject(FormBuilder);
  private readonly dialogRef = inject<MatDialogRef<GoalFormDialog, AddGoalRequest | EditGoalRequest>>(MatDialogRef);
  readonly data = inject<GoalFormDialogData>(MAT_DIALOG_DATA);

  readonly isEdit = !!this.data.goal;

  readonly form = this.fb.nonNullable.group({
    name: [this.data.goal?.name ?? '', Validators.required],
    description: [this.data.goal?.description ?? ''],
    base_xp_per_task: [this.data.goal?.base_xp_per_task ?? 10, [Validators.required, Validators.min(1)]],
    milestones: [this.data.goal ? this.data.goal.milestones.join(', ') : ''],
  });

  private parseMilestones(): number[] | undefined {
    const raw = this.form.controls.milestones.value.trim();
    if (!raw) return undefined;
    return raw
      .split(',')
      .map((part) => Number(part.trim()))
      .filter((n) => Number.isFinite(n) && n > 0);
  }

  save(): void {
    if (this.form.invalid) return;
    const { name, description, base_xp_per_task, milestones } = this.form.getRawValue();

    if (this.isEdit) {
      const request: EditGoalRequest = {
        name,
        base_xp_per_task,
        milestones: this.parseMilestones(),
      };
      this.dialogRef.close(request);
    } else {
      const request: AddGoalRequest = {
        name,
        description: description || undefined,
        base_xp_per_task,
        milestones: this.parseMilestones(),
      };
      this.dialogRef.close(request);
    }
  }

  cancel(): void {
    this.dialogRef.close();
  }
}
