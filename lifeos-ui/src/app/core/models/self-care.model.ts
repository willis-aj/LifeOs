/** Mirrors life_os_api.routers.self_care / life_os.self_care_agent.self_care_status(). */
export interface SelfCareSignals {
  consecutive_skips: number;
  overdue_ratio: number;
  overwhelm: boolean;
}

export interface SelfCareMessage {
  task_id: string;
  label: string;
  text: string;
  tone: string;
}

export interface SelfCareStatus {
  signals: SelfCareSignals;
  comfort_mode_active: boolean;
  comfort_mode_recommended: boolean;
  messages: SelfCareMessage[];
}
