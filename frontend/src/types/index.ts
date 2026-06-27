// ── Dynamic Guests ──────────────────────────────────
export interface GeneratedGuest {
  id: string;
  name: string;
  title: string;       // 职业/Title
  stance: string;      // 立场
  color: string;       // 专属颜色 #hex
  avatar: string;      // emoji
}

export interface GuestGenerateResponse {
  host: GeneratedGuest;
  experts: GeneratedGuest[];
}

// ── Message ─────────────────────────────────────────
export interface Message {
  id: string;
  session_id: string;
  phase: 'opening' | 'free_discussion' | 'summary';
  round: number;
  speaker_id: string;
  speaker_name: string;
  content: string;
  sequence: number;
  created_at: string;
}

// ── Session ─────────────────────────────────────────
export interface GuestBrief {
  id: string;
  name: string;
  avatar: string;
  title: string;
  color: string;
}

export interface SessionBrief {
  id: string;
  topic: string;
  guests: GuestBrief[];
  status: 'active' | 'completed' | 'error';
  message_count: number;
  created_at: string;
}

export interface SessionDetail {
  id: string;
  topic: string;
  guests: GuestBrief[];
  status: string;
  messages: Message[];
  created_at: string;
  completed_at: string | null;
}

// ── Expert Status ───────────────────────────────────
export type ExpertState = 'idle' | 'preparing' | 'ready' | 'speaking';

export interface ExpertStatusInfo {
  state: ExpertState;
  focus: string;  // 当前关注/思考摘要 (公开)
}

export interface ExpertStatusMap {
  [expertId: string]: ExpertStatusInfo;
}

// ── SSE Events ──────────────────────────────────────
export type SSEEventType =
  | 'connected' | 'phase_start'
  | 'moderator_opening' | 'free_discussion' | 'moderator_summary'
  | 'phase_end' | 'session_end' | 'done' | 'error'
  | 'expert_status' | 'consensus_update' | 'moderator_connect'
  | 'moderator_followup'
  | 'message_start' | 'message_chunk';

export interface SSEData {
  session_id?: string; topic?: string; phase?: string;
  round?: number; label?: string;
  speaker_id?: string; speaker_name?: string; content?: string;
  content_delta?: string;  // streaming chunk
  message?: string; code?: string;
  message_count?: number; duration_seconds?: number;
  status?: ExpertStatusMap;
  new_consensus?: string[]; new_divergence?: string[];
  all_consensus?: string[]; all_divergence?: string[];
  consensus?: string[]; divergence?: string[];
}

export interface SSEEvent {
  type: SSEEventType;
  data: SSEData;
}

// ── API ─────────────────────────────────────────────
export interface ApiResponse<T> { code: number; message: string; data: T; }
export interface PaginatedData<T> { items: T[]; total: number; page: number; page_size: number; }

// ── Discussion State ────────────────────────────────
export type DiscussionPhase =
  | 'connecting' | 'opening' | 'free_discussion' | 'summary' | 'completed' | 'error';

export interface DiscussionState {
  sessionId: string;
  topic: string;
  phase: DiscussionPhase;
  currentRound: number;
  messages: Message[];
  isConnected: boolean;
  error: string | null;
  expertStatus: ExpertStatusMap;
  consensusPoints: string[];
  divergencePoints: string[];
  pendingSpeakerId: string | null;
  pendingContent: string;
}
