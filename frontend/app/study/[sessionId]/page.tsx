'use client';
import { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { api, API_BASE, sessionCounts, QuestionResponse, AnswerResponse, SessionSummary } from '@/lib/api';
import NavBar from '@/components/NavBar';

type Phase = 'loading' | 'quiz' | 'confidence' | 'done';

// Derive the ordered list of available option letters from a question response.
// Renders A–G depending on which option_* fields are non-empty.
function getOptionKeys(q: QuestionResponse): string[] {
  const keys: string[] = [];
  if (q.option_a) keys.push('A');
  if (q.option_b) keys.push('B');
  if (q.option_c) keys.push('C');
  if (q.option_d) keys.push('D');
  if (q.option_e) keys.push('E');
  if (q.option_f) keys.push('F');
  if (q.option_g) keys.push('G');
  return keys;
}

// Build option map from question response
function getOptionMap(q: QuestionResponse): Record<string, string> {
  const map: Record<string, string> = {};
  if (q.option_a) map['A'] = q.option_a;
  if (q.option_b) map['B'] = q.option_b;
  if (q.option_c) map['C'] = q.option_c;
  if (q.option_d) map['D'] = q.option_d;
  if (q.option_e) map['E'] = q.option_e;
  if (q.option_f) map['F'] = q.option_f;
  if (q.option_g) map['G'] = q.option_g;
  return map;
}

export default function SessionPage() {
  const params = useParams();
  const sessionId = Number(params.sessionId);
  const router = useRouter();
  const { token } = useAuth();
  const startTime = useRef(Date.now());
  // Chosen confidence before submitting
  const busyRef = useRef(false);
  const [busy, setBusy] = useState(false);

  const [phase, setPhase] = useState<Phase>('loading');
  const [question, setQuestion] = useState<QuestionResponse | null>(null);
  const [questionNum, setQuestionNum] = useState(1);
  const [totalQuestions, setTotalQuestions] = useState<number | null>(null);
  // selected is a Set for multi-answer; empty = nothing chosen yet
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [answerResult, setAnswerResult] = useState<AnswerResponse | null>(null);
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const [error, setError] = useState('');

  const isMulti = question?.is_multi_answer ?? false;

  const finishSession = async () => {
    if (!token) return;
    const s = await api.sessions.complete(sessionId, token);
    sessionCounts.delete(sessionId);
    setSummary(s); setPhase('done');
  };
  const fetchQuestion = async () => {
    if (!token) return;
    const q = await api.sessions.next(sessionId, token);
    if (!q) { await finishSession(); return; }
    setQuestion(q); setSelected(new Set()); setAnswerResult(null);
    setPhase('quiz'); startTime.current = Date.now();
  };
  const run = async (action: () => Promise<void>) => {
    if (busyRef.current) return;
    busyRef.current = true; setBusy(true); setError('');
    try { await action(); } catch (err) { setError(err instanceof Error ? err.message : 'Request failed'); }
    finally { busyRef.current = false; setBusy(false); }
  };
  useEffect(() => {
    if (!token) return;
    setTotalQuestions(sessionCounts.get(sessionId) ?? null);
    void run(fetchQuestion);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, !!token]);
  const submitWithConfidence = async (confidence: 'again' | 'hard' | 'good' | 'easy') => {
    if (!selected.size || !token || !question || phase !== 'quiz') return;
    await run(async () => {
      const result = await api.sessions.answer(sessionId, {
        question_id: question.id, selected_options: Array.from(selected), confidence,
        response_time_ms: Date.now() - startTime.current,
      }, token);
      setAnswerResult(result); setPhase('confidence');
    });
  };
  const handleNext = () => run(async () => {
    await fetchQuestion(); setQuestionNum(n => n + 1);
  });
  const toggleOption = (key: string) => {
    if (phase !== 'quiz' || busyRef.current) return;
    setSelected(prev => {
      if (!isMulti) return new Set([key]);
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  };

  const getOptionStyle = (key: string) => {
    const isSelected = selected.has(key);

    if (phase === 'loading' || phase === 'quiz') {
      if (!isSelected) return { background: 'white' };
      return { background: '#dbeafe', borderColor: '#2563eb' };
    }

    // After answer — show correct/incorrect based on answer result
    if (!answerResult) return { background: 'white' };
    const correctLetters = answerResult.correct_option.split('');
    const userLetters = answerResult.user_selection.split('');
    const wasSelected = userLetters.includes(key);
    const isCorrectLetter = correctLetters.includes(key);

    if (isCorrectLetter) {
      return { background: '#d1fae5', borderColor: '#10b981' };
    }
    if (wasSelected) {
      return { background: '#fee2e2', borderColor: '#ef4444', opacity: 1 };
    }
    return { background: 'white', opacity: 1 };
  };

  // Checkbox indicator for multi-answer; letter prefix for single-answer
  const optionPrefix = (key: string) => {
    if (isMulti) return selected.has(key) ? '☑' : '☐';
    return `${key}.`;
  };

  if (phase === 'loading') return (
    <div><NavBar /><div className="container page">{error ? <><p role="alert">{error}</p><button disabled={busy} onClick={() => run(fetchQuestion)}>Retry</button><button onClick={() => router.push('/study')}>New Session</button></> : <p>Loading question...</p>}</div></div>
  );

  if (phase === 'done' && summary) {
    const pct = summary.accuracy_pct;
    return (
      <div>
        <NavBar />
        <div className="container page" style={{ textAlign: 'center' }}>
          <div className="card" style={{ maxWidth: '480px', margin: '0 auto' }}>
            <h1 style={{ marginBottom: '1.5rem' }}>Session Complete!</h1>
            <div style={{ fontSize: '3rem', fontWeight: 700, color: pct >= 80 ? '#10b981' : pct >= 60 ? '#f59e0b' : '#ef4444' }}>
              {summary.correct_count}/{summary.questions_shown}
            </div>
            <p style={{ color: '#6b7280', margin: '0.5rem 0 2rem' }}>{pct}% accuracy</p>
            <div style={{ background: '#f3f4f6', borderRadius: '8px', padding: '1rem', marginBottom: '1.5rem', textAlign: 'left' }}>
              {pct >= 80 ? 'Excellent work! Keep it up.' : pct >= 60 ? 'Good effort. Focus on the weak areas.' : 'Keep studying! Review explanations and try again.'}
            </div>
            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', flexWrap: 'wrap' }}>
              <button onClick={() => router.push('/dashboard')}>Dashboard</button>
              <button className="secondary" onClick={() => router.push('/study')}>New Session</button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!question) return (
    <div><NavBar /><div className="container page"><p>Error loading question.</p></div></div>
  );

  const q = question;
  const optionKeys = getOptionKeys(q);
  const optionMap = getOptionMap(q);
  const correctLetters = answerResult?.correct_option.split('') ?? [];
  const userLetters = answerResult?.user_selection.split('') ?? [];

  return (
    <div>
      <NavBar />
      <div className="container page">
        {/* Progress bar */}
        <div style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.5rem' }}>
            <span>Question {questionNum}{totalQuestions ? ` of ${totalQuestions}` : ''}</span>
            <span>{q.book_title}</span>
          </div>
          <div style={{ background: '#e5e7eb', height: '4px', borderRadius: '2px' }}>
            <div style={{
              background: '#2563eb', height: '100%', borderRadius: '2px',
              width: `${totalQuestions ? Math.min(100, Math.round(questionNum / totalQuestions * 100)) : 0}%`, transition: 'width 0.3s'
            }} />
          </div>
        </div>

        {/* Multi-answer hint */}
        {isMulti && phase === 'quiz' && (
          <div style={{ background: '#fef9c3', border: '1px solid #f59e0b', borderRadius: '6px', padding: '0.5rem 0.75rem', marginBottom: '1rem', fontSize: '0.875rem', color: '#92400e' }}>
            Select all correct answers
          </div>
        )}

        {/* Question text */}
        <div className="card" style={{ marginBottom: '1.5rem', background: '#f8fafc' }}>
          <p style={{ fontSize: '1.05rem', lineHeight: 1.6 }}>{q.question_text}</p>
          {q.question_image && <img src={`${API_BASE}/api/images/${encodeURIComponent(q.question_image.split('/').pop()!)}`} alt="Question diagram" style={{ maxWidth: '100%', marginTop: '1rem' }} />}
        </div>

        {/* Options */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1.5rem' }}>
          {optionKeys.map(key => (
            <button
              key={key}
              onClick={() => toggleOption(key)}
              disabled={busy || phase !== 'quiz'}
              style={{
                display: 'flex', gap: '0.75rem', padding: '0.875rem 1rem',
                textAlign: 'left', color: '#111827', borderWidth: '2px', borderStyle: 'solid', borderColor: '#d1d5db', borderRadius: '8px',
                cursor: phase === 'quiz' ? 'pointer' : 'default',
                transition: 'all 0.15s', fontSize: '1rem', fontFamily: 'inherit',
                width: '100%', ...getOptionStyle(key),
              }}
            >
              <span style={{ fontWeight: 700, minWidth: '24px', color: '#6b7280' }}>
                {optionPrefix(key)}
              </span>
              <span>{optionMap[key]}</span>
            </button>
          ))}
        </div>

        {/* Submit (quiz phase) — submit with actual confidence */}
        {phase === 'quiz' && (
          <div>
            <p style={{ fontWeight: 500, marginBottom: '0.5rem' }}>How confident are you?</p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <button
                onClick={() => submitWithConfidence('again')}
                disabled={busy || selected.size === 0}
                style={{ background: '#b91c1c', padding: '0.75rem', opacity: selected.size === 0 ? 0.5 : 1 }}
              >
                Again<span style={{ display: 'block', fontSize: '0.75rem', fontWeight: 400 }}>1 day</span>
              </button>
              <button
                onClick={() => submitWithConfidence('hard')}
                disabled={busy || selected.size === 0}
                style={{ background: '#92400e', padding: '0.75rem', opacity: selected.size === 0 ? 0.5 : 1 }}
              >
                Hard<span style={{ display: 'block', fontSize: '0.75rem', fontWeight: 400 }}>Shorter</span>
              </button>
              <button
                onClick={() => submitWithConfidence('good')}
                disabled={busy || selected.size === 0}
                style={{ background: '#047857', padding: '0.75rem', opacity: selected.size === 0 ? 0.5 : 1 }}
              >
                Good<span style={{ display: 'block', fontSize: '0.75rem', fontWeight: 400 }}>Normal</span>
              </button>
              <button
                onClick={() => submitWithConfidence('easy')}
                disabled={busy || selected.size === 0}
                style={{ background: '#2563eb', padding: '0.75rem', opacity: selected.size === 0 ? 0.5 : 1 }}
              >
                Easy<span style={{ display: 'block', fontSize: '0.75rem', fontWeight: 400 }}>Longer</span>
              </button>
            </div>
            <p style={{ fontSize: '0.8rem', color: '#6b7280', textAlign: 'center' }}>
              Submit your answer and confidence together
            </p>
          </div>
        )}

        {/* Confidence phase — show result and explanation */}
        {phase === 'confidence' && answerResult && (
          <div>
            {/* Result banner */}
            <div style={{
              padding: '1rem', borderRadius: '8px', marginBottom: '1rem',
              background: answerResult.is_correct ? '#d1fae5' : '#fee2e2',
            }}>
              <p style={{ fontWeight: 600, fontSize: '1.1rem' }}>
                {answerResult.is_correct ? 'Correct!' : 'Incorrect'}
              </p>
              <p style={{ fontSize: '0.95rem', marginTop: '0.25rem' }}>
                Your answer: {userLetters.join(', ') || '(none)'}
                &nbsp;&nbsp;|&nbsp;&nbsp;
                Correct: {correctLetters.join(', ')}
              </p>
            </div>

            {/* Explanation */}
            <div style={{ background: '#f9fafb', padding: '1rem', borderRadius: '8px', marginBottom: '1rem' }}>
              <h4 style={{ marginBottom: '0.5rem' }}>Explanation</h4>
              <p style={{ fontSize: '0.9rem', lineHeight: 1.6 }}>{answerResult.explanation}</p>
              {answerResult.ocg_chapter_ref && (
                <p style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: '#6b7280' }}>
                  Reference: OCG Chapter {answerResult.ocg_chapter_ref}
                </p>
              )}
              {answerResult.mastered && (
                <p style={{ marginTop: '0.5rem', color: '#10b981', fontWeight: 500 }}>
                  Mastered! Next review in {answerResult.next_review_days} days.
                </p>
              )}
            </div>

            <button disabled={busy} onClick={handleNext} style={{ width: '100%', padding: '0.875rem', fontSize: '1rem' }}>
              {totalQuestions && questionNum >= totalQuestions ? 'Finish Session' : 'Next Question'}
            </button>
          </div>
        )}

        {error && <p style={{ color: '#dc2626', marginTop: '1rem', textAlign: 'center' }}>{error}</p>}
      </div>
    </div>
  );
}
