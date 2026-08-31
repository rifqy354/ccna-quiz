/** API client wrapper with auth header injection. */
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type FetchOptions = RequestInit & { token?: string };

async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { token, ...fetchOpts } = options;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(fetchOpts.headers as Record<string, string> || {}),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...fetchOpts, headers });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

export interface DomainSummary {
  domain: number; name: string; total_questions: number;
  mastered: number; attempted: number;
}
export interface DomainDetail {
  domain: number; name: string;
  sub_domains: { sub_domain: string; sub_domain_name: string; cnt: number }[];
}
export interface QuestionResponse {
  id: number; source_book: string; source_chapter: string; book_title: string;
  domain?: number; sub_domain?: string; sub_domain_name?: string;
  question_text: string; question_image?: string;
  option_a: string; option_b: string; option_c: string; option_d: string;
}
export interface AnswerData {
  question_id: number; selected_option: string;
  confidence: 'again' | 'hard' | 'good' | 'easy'; response_time_ms?: number;
}
export interface AnswerResponse {
  is_correct: boolean; correct_option: string; explanation: string;
  ocg_chapter_ref?: string; ocg_section_ref?: string;
  mastered: boolean; next_review_days: number;
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
  auth: {
    register: (data: { email: string; password: string; name: string }) =>
      apiFetch<{ id: number; email: string; name: string }>('/api/auth/register', {
        method: 'POST', body: JSON.stringify(data),
      }),
    login: (data: { email: string; password: string }) =>
      apiFetch<{ access_token: string; refresh_token: string }>('/api/auth/login', {
        method: 'POST', body: JSON.stringify(data),
      }),
    refresh: (refresh_token: string) =>
      apiFetch<{ access_token: string; refresh_token: string }>('/api/auth/refresh', {
        method: 'POST', body: JSON.stringify({ refresh_token }),
      }),
    me: (token: string) =>
      apiFetch<{ id: number; email: string; name: string }>('/api/auth/me', { token }),
  },
  domains: {
    list: (token: string) => apiFetch<DomainSummary[]>('/api/domains', { token }),
    get: (domain: number, token: string) =>
      apiFetch<DomainDetail>(`/api/domains/${domain}`, { token }),
  },
  sessions: {
    start: (data: { domain?: number; session_type: string; count: number }, token: string) =>
      apiFetch<SessionStartResponse>('/api/sessions/start', {
        method: 'POST', body: JSON.stringify(data), token,
      }),
    next: (sessionId: number, token: string) =>
      apiFetch<QuestionResponse>(`/api/sessions/${sessionId}/next`, { token }),
    answer: (sessionId: number, data: AnswerData, token: string) =>
      apiFetch<AnswerResponse>(`/api/sessions/${sessionId}/answer`, {
        method: 'POST', body: JSON.stringify(data), token,
      }),
    complete: (sessionId: number, token: string) =>
      apiFetch<SessionSummary>(`/api/sessions/${sessionId}/complete`, { method: 'POST', token }),
  },
  stats: {
    dashboard: (token: string) => apiFetch<DashboardStats>('/api/stats/dashboard', { token }),
  },
};
