import { Component, input, output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

import { LifeTask, PUSH_REASON_LABELS } from '../../core/models/task.model';

/** A single task row/card with complete/skip/edit/delete/pull-forward
 * actions. Purely presentational - the parent view owns the actual
 * service calls and decides which actions to wire up via
 * `showPullForward` (day/backlog show it, home doesn't need to since
 * pulling into "now" from "now" is a no-op). */
@Component({
  selector: 'app-task-item',
  imports: [MatButtonModule, MatIconModule, MatChipsModule, MatTooltipModule],
  templateUrl: './task-item.html',
  styleUrl: './task-item.scss',
})
export class TaskItem {
  readonly task = input.required<LifeTask>();
  readonly showPullForward = input(false);
  readonly showHour = input(true);
  readonly compact = input(false);

  readonly complete = output<LifeTask>();
  readonly skip = output<LifeTask>();
  readonly edit = output<LifeTask>();
  readonly delete = output<LifeTask>();
  readonly pullForward = output<LifeTask>();

  readonly pushReasonLabels = PUSH_REASON_LABELS;

  formatHour(hour: number): string {
    const period = hour < 12 ? 'AM' : 'PM';
    let display = hour % 12;
    if (display === 0) {
      display = 12;
    }
    return `${display}:00 ${period}`;
  }
}
