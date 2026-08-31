const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function apiFetch<T>(path: string, token?: string, body?: object): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, {
    method: body ? 'POST' : 'GET',
    headers,
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(e.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export interface DomainSummary {
  domain: number; name: string; total_questions: number;
  mastered: number; attempted: number;
}

export interface QuestionResponse {
  id: number; source_book: string; source_chapter: string; book_title: string;
  domain: number; sub_domain?: string; sub_domain_name?: string;
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
      apiFetch<QuestionResponse>(`/api/sessions/${sessionId}/next`, token),
    answer: (sessionId: number, data: AnswerData, token: string) =>
      apiFetch<AnswerResponse>(`/api/sessions/${sessionId}/answer`, token, data),
    complete: (sessionId: number, token: string) =>
      apiFetch<SessionSummary>(`/api/sessions/${sessionId}/complete`, token),
  },
  stats: {
    dashboard: (token: string) =>
      apiFetch<DashboardStats>('/api/stats/dashboard', token),
  },
};
