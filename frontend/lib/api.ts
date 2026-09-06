export const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/$/, '');
let refreshHandler: (() => Promise<string | null>) | null = null;
export function setRefreshHandler(handler: typeof refreshHandler) { refreshHandler = handler; }
export async function apiFetch<T>(path: string, token?: string, body?: object, method = body ? 'POST' : 'GET'): Promise<T> {
  const request = (access?: string) => fetch(`${API_BASE}${path}`, {
    method, headers: { 'Content-Type': 'application/json', ...(access ? { Authorization: `Bearer ${access}` } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  let res = await request(token);
  if (res.status === 401 && token && refreshHandler) {
    const refreshed = await refreshHandler();
    if (refreshed) res = await request(refreshed);
  }
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    const detail = Array.isArray(e.detail) ? e.detail.map((v: {msg?: string}) => v.msg || 'Invalid input').join('; ') : e.detail;
    throw new Error(typeof detail === 'string' ? detail : `Request failed (HTTP ${res.status})`);
  }
  return res.status === 204 ? null as T : res.json();
}

// Volatile UI metadata only; study sessions are never saved in browser storage.
export const sessionCounts = new Map<number, number>();

export interface DomainSummary {
  domain: number; name: string; total_questions: number;
  mastered: number; attempted: number;
}

export interface QuestionResponse {
  id: number;
  source_book: string;
  source_chapter: string;
  book_title: string;
  domain: number;
  sub_domain?: string;
  sub_domain_name?: string;
  question_text: string;
  question_image?: string;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
  option_e?: string;
  option_f?: string;
  option_g?: string;
  is_multi_answer: boolean;   // true when correct answer requires multiple selections
}

export interface AnswerData {
  question_id: number;
  selected_options: string[];  // e.g. ["A"] or ["B", "D", "E"]
  confidence: 'again' | 'hard' | 'good' | 'easy';
  response_time_ms?: number;
}

export interface AnswerResponse {
  is_correct: boolean;
  correct_option: string;
  user_selection: string;      // canonical form of what user selected, e.g. "BDE"
  explanation: string;
  ocg_chapter_ref?: string;
  ocg_section_ref?: string;
  mastered: boolean;
  next_review_days: number;
}

export interface SessionStartResponse {
  session_id: number; total_questions: number; session_type: string;
}

export interface SessionSummary {
  session_id: number; questions_shown: number; correct_count: number;
  accuracy_pct: number; completed_at: string;
}

export interface DashboardStats {
  total_questions: number; questions_mastered: number; questions_attempted: number;
  overall_recall_rate: number; study_streak: number; due_today: number;
  domains: DomainSummary[];
}

export const api = {
  domains: {
    list: (token: string) =>
      apiFetch<DomainSummary[]>('/api/domains', token),
    get: (domain: number, token: string) =>
      apiFetch<{ domain: number; name: string; sub_domains: any[] }>(`/api/domains/${domain}`, token),
  },
  sessions: {
    start: (data: { domain?: number; session_type: string; count: number }, token: string) =>
      apiFetch<SessionStartResponse>('/api/sessions/start', token, data),
    next: (sessionId: number, token: string) =>
      apiFetch<QuestionResponse | null>(`/api/sessions/${sessionId}/next`, token),
    answer: (sessionId: number, data: AnswerData, token: string) =>
      apiFetch<AnswerResponse>(`/api/sessions/${sessionId}/answer`, token, data),
    complete: (sessionId: number, token: string) =>
      apiFetch<SessionSummary>(`/api/sessions/${sessionId}/complete`, token, undefined, 'POST'),
  },
  stats: {
    dashboard: (token: string) =>
      apiFetch<DashboardStats>('/api/stats/dashboard', token),
  },
};
