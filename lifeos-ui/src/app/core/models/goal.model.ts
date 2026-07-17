/** Mirrors the dict shape returned by life_os.engine.goal_progress(). */
export interface GoalProgress {
  id: string;
  name: string;
  description: string;
  base_xp_per_task: number;
  xp: number;
  level: number;
  milestones: number[];
  milestones_reached: number[];
  next_milestone: number | null;
}

export interface AddGoalRequest {
  name: string;
  description?: string;
  base_xp_per_task?: number;
  milestones?: number[];
}

export interface EditGoalRequest {
  name?: string;
  base_xp_per_task?: number;
  milestones?: number[];
}
