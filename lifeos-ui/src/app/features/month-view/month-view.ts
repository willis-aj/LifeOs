import { Component, OnInit, signal } from '@angular/core';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { ScheduleService } from '../../core/services/schedule.service';
import { NotifyService } from '../../core/services/notify.service';
import { PlayerContextService } from '../../core/state/player-context.service';
import { CalendarCell, MonthCalendarView } from '../../core/models/task.model';
import { DayDetailDialog, DayDetailDialogData } from '../../shared/day-detail-dialog/day-detail-dialog';

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];
const WEEKDAY_HEADERS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MAX_LABELS_SHOWN = 3;

/** A true 7-column (Sun-Sat) calendar grid for the current month. Each
 * day is a box; task/event labels wrap inside it, and a box that would
 * overflow shows "+N more" instead of spilling into neighboring days.
 * Clicking a day opens a modal with the full list. Boss fights, routines,
 * and one-off scheduled events are all included - see
 * engine.month_calendar_view() on the Python side. */
@Component({
  selector: 'app-month-view',
  imports: [MatButtonModule, MatIconModule, MatProgressSpinnerModule],
  templateUrl: './month-view.html',
  styleUrl: './month-view.scss',
})
export class MonthView implements OnInit {
  readonly loading = signal(true);
  readonly view = signal<MonthCalendarView | null>(null);
  readonly weekdayHeaders = WEEKDAY_HEADERS;
  readonly maxLabelsShown = MAX_LABELS_SHOWN;

  private year = new Date().getFullYear();
  private month = new Date().getMonth() + 1;

  constructor(
    private readonly scheduleService: ScheduleService,
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

  get monthLabel(): string {
    return `${MONTH_NAMES[this.month - 1]} ${this.year}`;
  }

  reload(): void {
    const playerId = this.playerContext.playerId();
    if (!playerId) return;
    this.loading.set(true);
    this.scheduleService.getMonth(playerId, this.year, this.month).subscribe({
      next: (view) => {
        this.view.set(view);
        this.year = view.year;
        this.month = view.month;
        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        this.notify.error(err);
      },
    });
  }

  previousMonth(): void {
    this.month -= 1;
    if (this.month < 1) {
      this.month = 12;
      this.year -= 1;
    }
    this.reload();
  }

  nextMonth(): void {
    this.month += 1;
    if (this.month > 12) {
      this.month = 1;
      this.year += 1;
    }
    this.reload();
  }

  visibleLabels(cell: CalendarCell): string[] {
    return cell.labels.slice(0, this.maxLabelsShown);
  }

  overflowCount(cell: CalendarCell): number {
    return Math.max(0, cell.labels.length - this.maxLabelsShown);
  }

  openDayDetail(cell: CalendarCell | null): void {
    if (!cell) return;
    const data: DayDetailDialogData = {
      year: this.year,
      month: this.month,
      day: cell.day,
      labels: cell.labels,
    };
    this.dialog.open(DayDetailDialog, { width: '420px', data });
  }
}
