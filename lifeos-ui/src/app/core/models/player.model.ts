export interface PlayerSummary {
  id: string;
  name: string;
  created_at: string;
}

export type EnergyMode = 'low' | 'normal' | 'high';

/** Mirrors life_os_api.deps.serialize_state(). */
export interface PlayerState {
  xp: number;
  level: number;
  xp_into_level: number;
  xp_to_next: number;
  streak_days: number;
  longest_streak: number;
  energy_mode: EnergyMode;
  chaos_mode: boolean;
  comfort_mode: boolean;
  mode_label: string;
  companion_id: string;
  current_season_id: string | null;
  inventory: string[];
  boss_fights_won: number;
  tasks_completed_total: number;
  tasks_skipped_total: number;
}

export interface CheckinSummary {
  rolled_over: boolean;
  days_advanced: number;
  carried_count: number;
  overdue_moved_count: number;
  dependency_fixes: { prerequisite: string; dependent: string }[];
}

export interface PlayerDetail {
  id: string;
  name: string;
  state: PlayerState;
  companion_message: string;
  checkin: CheckinSummary | null;
}
