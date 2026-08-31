\
'use client';
import { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { api, QuestionResponse, AnswerResponse, SessionSummary } from '@/lib/api';
import NavBar from '@/components/NavBar';

type Phase = 'loading' | 'quiz' | 'answering' | 'confidence' | 'done';

const OPTIONS = ['A', 'B', 'C', 'D'] as const;
type Option = typeof OPTIONS[number];

export default function SessionPage() {
  const params = useParams();
  const sessionId = Number(params.sessionId);
  const router = useRouter();
  const { token } = useAuth();
  const startTime = useRef(Date.now());

  const [phase, setPhase] = useState<Phase>('loading');
  const [question, setQuestion] = useState<QuestionResponse | null>(null);
  const [questionNum, setQuestionNum] = useState(1);
  const [totalQuestions, setTotalQuestions] = useState(20);
  const [selected, setSelected] = useState<Option | null>(null);
  const [answerResult, setAnswerResult] = useState<AnswerResponse | null>(null);
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const [error, setError] = useState('');

  const fetchQuestion = async () => {
    if (!token) return;
    try {
      const q = await api.sessions.next(sessionId, token);
      setQuestion(q);
      setSelected(null);
      setAnswerResult(null);
      setPhase('quiz');
      startTime.current = Date.now();
    } catch (err: any) {
      if (err.message?.includes('No more') || err.message?.includes('detail')) {
        await finishSession();
      } else {
        setError(err.message);
      }
    }
  };

  const finishSession = async () => {
    if (!token) return;
    try {
      const s = await api.sessions.complete(sessionId, token);
      setSummary(s);
      setPhase('done');
    } catch (err: any) {
      setError(err.message);
    }
  };

  useEffect(() => {
    if (!token) return;
    const storedCount = parseInt(sessionStorage.getItem(`session_${sessionId}_count`) || '20');
    setTotalQuestions(storedCount);
    fetchQuestion();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, sessionId]);

  const submitAnswer = async () => {
    if (!selected || !token || !question) return;
    const responseTime = Date.now() - startTime.current;
    const result = await api.sessions.answer(sessionId, {
      question_id: question.id,
      selected_option: selected,
      confidence: 'good',
      response_time_ms: responseTime,
    }, token);
    setAnswerResult(result);
    setPhase('confidence');
  };

  const submitConfidence = async (conf: 'again' | 'hard' | 'good' | 'easy') => {
    if (!token || !question) return;
    // Re-answer with actual confidence (first answer used 'good' as placeholder)
    const result = await api.sessions.answer(sessionId, {
      question_id: question.id,
      selected_option: selected!,
      confidence: conf,
      response_time_ms: Date.now() - startTime.current,
    }, token);
    setAnswerResult(result);
    setPhase('done');
  };

  const handleNext = async () => {
    setQuestionNum(n => n + 1);
    await fetchQuestion();
  };

  const getOptionStyle = (key: Option) => {
    if (phase === 'loading' || phase === 'quiz') {
      return selected === key
        ? { background: '#dbeafe', borderColor: '#2563eb' }
        : { background: 'white' };
    }
    if (phase === 'answering') {
      return { background: '#dbeafe', borderColor: '#2563eb' };
    }
    // After answer
    const correct = answerResult?.correct_option === key;
    const wrong = selected === key && !correct;
    if (correct) return { background: '#d1fae5', borderColor: '#10b981' };
    if (wrong) return { background: '#fee2e2', borderColor: '#ef4444', opacity: 0.6 };
    return { background: 'white', opacity: 0.5 };
  };

  if (phase === 'loading') return <div><NavBar /><div className="container page"><p>Loading question...</p></div></div>;

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

  if (!question) return <div><NavBar /><div className="container page"><p>Error loading question.</p></div></div>;

  const q = question;
  const optionMap: Record<Option, string> = { A: q.option_a, B: q.option_b, C: q.option_c, D: q.option_d };

  return (
    <div>
      <NavBar />
      <div className="container page">
        {/* Progress bar */}
        <div style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.5rem' }}>
            <span>Question {questionNum} of {totalQuestions}</span>
            <span>{q.book_title}</span>
          </div>
          <div style={{ background: '#e5e7eb', height: '4px', borderRadius: '2px' }}>
            <div style={{
              background: '#2563eb', height: '100%', borderRadius: '2px',
              width: `${Math.round(questionNum / totalQuestions * 100)}%`, transition: 'width 0.3s'
            }} />
          </div>
        </div>

        {/* Question text */}
        <div className="card" style={{ marginBottom: '1.5rem', background: '#f8fafc' }}>
          <p style={{ fontSize: '1.05rem', lineHeight: 1.6 }}>{q.question_text}</p>
        </div>

        {/* Options */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1.5rem' }}>
          {OPTIONS.map(key => (
            <button
              key={key}
              onClick={() => phase === 'quiz' && setSelected(key)}
              disabled={phase !== 'quiz'}
              style={{
                display: 'flex', gap: '0.75rem', padding: '0.875rem 1rem',
                textAlign: 'left', border: '2px solid #d1d5db', borderRadius: '8px',
                cursor: phase === 'quiz' ? 'pointer' : 'default',
                transition: 'all 0.15s', fontSize: '1rem', ...getOptionStyle(key),
              }}
            >
              <span style={{ fontWeight: 700, minWidth: '24px', color: '#6b7280' }}>{key}.</span>
              <span>{optionMap[key]}</span>
            </button>
          ))}
        </div>

        {/* Submit */}
        {phase === 'quiz' && (
          <button onClick={submitAnswer} disabled={!selected} style={{ width: '100%', padding: '0.875rem', fontSize: '1rem' }}>
            Submit Answer
          </button>
        )}

        {/* Confidence buttons */}
        {phase === 'confidence' && answerResult && (
          <div style={{ marginTop: '1rem' }}>
            {/* Result banner */}
            <div style={{
              padding: '1rem', borderRadius: '8px', marginBottom: '1rem',
              background: answerResult.is_correct ? '#d1fae5' : '#fee2e2',
            }}>
              <p style={{ fontWeight: 600, fontSize: '1.1rem' }}>
                {answerResult.is_correct
                  ? `Correct! Answer: ${answerResult.correct_option}`
                  : `Incorrect. Answer: ${answerResult.correct_option}`}
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
            <p style={{ fontWeight: 500, marginBottom: '0.75rem' }}>How confident are you?</p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
              <button onClick={() => submitConfidence('again')} style={{ background: '#ef4444', padding: '0.75rem' }}>
                Again<span style={{ display: 'block', fontSize: '0.75rem', fontWeight: 400 }}>1 day</span>
              </button>
              <button onClick={() => submitConfidence('hard')} style={{ background: '#f59e0b', padding: '0.75rem' }}>
                Hard<span style={{ display: 'block', fontSize: '0.75rem', fontWeight: 400 }}>Shorter</span>
              </button>
              <button onClick={() => submitConfidence('good')} style={{ background: '#10b981', padding: '0.75rem' }}>
                Good<span style={{ display: 'block', fontSize: '0.75rem', fontWeight: 400 }}>Normal</span>
              </button>
              <button onClick={() => submitConfidence('easy')} style={{ background: '#3b82f6', padding: '0.75rem' }}>
                Easy<span style={{ display: 'block', fontSize: '0.75rem', fontWeight: 400 }}>Longer</span>
              </button>
            </div>
          </div>
        )}

        {/* Done phase - next button */}
        {phase === 'done' && (
          <button onClick={handleNext} style={{ width: '100%', padding: '0.875rem', fontSize: '1rem' }}>
            Next Question
          </button>
        )}

        {error && <p style={{ color: '#dc2626', marginTop: '1rem', textAlign: 'center' }}>{error}</p>}
      </div>
    </div>
  );
}
