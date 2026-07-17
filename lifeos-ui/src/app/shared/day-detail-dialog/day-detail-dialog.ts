import { Component, Inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';

export interface DayDetailDialogData {
  year: number;
  month: number; // 1-12
  day: number;
  labels: string[];
}

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

/** Full-detail popup for a single calendar day, opened by clicking a box
 * in the month view grid. The month view only has event *labels* for each
 * day (routine projections + one-off scheduled events), not full task
 * objects, so this is a read-only listing. */
@Component({
  selector: 'app-day-detail-dialog',
  imports: [MatDialogModule, MatListModule, MatIconModule, MatButtonModule],
  templateUrl: './day-detail-dialog.html',
  styleUrl: './day-detail-dialog.scss',
})
export class DayDetailDialog {
  readonly monthName: string;

  constructor(@Inject(MAT_DIALOG_DATA) public data: DayDetailDialogData) {
    this.monthName = MONTH_NAMES[data.month - 1] ?? '';
  }
}
