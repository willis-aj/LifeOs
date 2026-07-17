import type { GoalProgress } from './goal.model';

/** Mirrors life_os.models.Task (as serialized by life_os_api's serialize_task). */
export interface LifeTask {
  id: string;
  label: string;
  goal: string;
  goal_name: string;
  scheduled_hour: number;
  scheduled_date: string;
  duration_minutes: number;
  xp: number;
  boss: boolean;
  completed: boolean;
  skipped: boolean;
  source_routine_id: string | null;
  dependencies: string[];
  locked: boolean;
  lock_reason: string | null;
  push_reason: PushReason | null;
  is_scheduling_task: boolean;
}

export type PushReason = 'skip' | 'dependency_push' | 'hour_drift' | 'eod_rollover';

export const PUSH_REASON_LABELS: Record<PushReason, string> = {
  skip: 'skipped',
  dependency_push: 'dependency push',
  hour_drift: 'hour drift',
  eod_rollover: 'end-of-day rollover',
};

export interface HourGroup {
  hour: number;
  tasks: LifeTask[];
}

export interface BacklogDayEntry {
  date: string;
  tasks: LifeTask[];
}

export interface BacklogView {
  pushed_today: LifeTask[];
  tomorrow: LifeTask[];
  later_this_week: BacklogDayEntry[];
}

export interface CalendarCell {
  day: number;
  labels: string[];
}

export interface MonthCalendarView {
  year: number;
  month: number;
  weeks: (CalendarCell | null)[][];
  goals: GoalProgress[];
}
