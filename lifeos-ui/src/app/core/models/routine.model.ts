export type RoutineFrequency = 'daily' | 'weekly' | 'monthly' | 'every_n_days' | 'once';

export interface Routine {
  id: string;
  label: string;
  goal: string;
  frequency: RoutineFrequency;
  time_of_day: number | null;
  duration_minutes: number;
  xp: number;
  boss: boolean;
  interval_days: number | null;
  requires: string[];
  is_scheduling_task: boolean;
  last_completed_date: string | null;
  missed_dates: string[];
}
