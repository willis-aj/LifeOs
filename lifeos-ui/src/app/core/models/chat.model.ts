/** Mirrors the message dicts life_os_api.routers.self_care_chat /
 * life_os.self_care_agent_chat return and persist. */
export type ChatPersona = 'system' | 'self_care_agent' | 'user';

export interface ChatMessage {
  speaker: ChatPersona;
  text: string;
  timestamp: string;
}

export interface ChatResponse {
  messages: ChatMessage[];
}
