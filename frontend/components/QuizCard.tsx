'use client';
import { QuestionResponse, AnswerResponse } from '@/lib/api';

interface QuizCardProps {
  question: QuestionResponse;
  questionNumber: number;
  totalQuestions: number;
  onSubmit: (selected: string) => void;
  answerResult?: AnswerResponse;
  showResult: boolean;
  selectedOption: string | null;
  onOptionChange: (opt: string) => void;
}

// Derive the ordered list of available option letters from a question response.
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

export default function QuizCard({
  question, questionNumber, totalQuestions,
  onSubmit, answerResult, showResult, selectedOption, onOptionChange,
}: QuizCardProps) {
  const getStyle = (key: string) => {
    if (!showResult) {
      return selectedOption === key
        ? { background: '#dbeafe', borderColor: '#2563eb' }
        : { background: 'white' };
    }
    const correct = key === answerResult?.correct_option;
    const wrong = selectedOption === key && !correct;
    if (correct) return { background: '#d1fae5', borderColor: '#10b981' };
    if (wrong) return { background: '#fee2e2', borderColor: '#ef4444', opacity: 1 };
    return { background: 'white', opacity: 1 };
  };

  const optionKeys = getOptionKeys(question);
  const optionMap = getOptionMap(question);

  return (
    <div>
      {/* Progress */}
      <div style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.5rem' }}>
          <span>Question {questionNumber} of {totalQuestions}</span>
          <span style={{ background: '#e5e7eb', padding: '0.125rem 0.5rem', borderRadius: '9999px' }}>{question.book_title}</span>
        </div>
        <div style={{ background: '#e5e7eb', height: '4px', borderRadius: '2px' }}>
          <div style={{ background: '#2563eb', height: '100%', borderRadius: '2px', width: `${Math.round(questionNumber / totalQuestions * 100)}%`, transition: 'width 0.3s' }} />
        </div>
      </div>

      {/* Question */}
      <div style={{ background: '#f8fafc', padding: '1.25rem', borderRadius: '10px', marginBottom: '1rem', border: '1px solid #e5e7eb' }}>
        <p style={{ fontSize: '1.05rem', lineHeight: 1.7 }}>{question.question_text}</p>
      </div>

      {/* Options */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem', marginBottom: '1rem' }}>
        {optionKeys.map(key => (
          <button
            key={key}
            onClick={() => !showResult && onOptionChange(key)}
            disabled={showResult}
            style={{
              display: 'flex', gap: '0.75rem', padding: '0.875rem 1rem',
              textAlign: 'left', color: '#111827', border: '2px solid #d1d5db', borderRadius: '8px',
              cursor: showResult ? 'default' : 'pointer', transition: 'all 0.15s',
              fontSize: '1rem', fontFamily: 'inherit', width: '100%', ...getStyle(key),
            }}
          >
            <span style={{ fontWeight: 700, minWidth: '28px', color: '#6b7280' }}>{key}.</span>
            <span>{optionMap[key]}</span>
          </button>
        ))}
      </div>

      {/* Submit */}
      {!showResult && (
        <button onClick={() => onSubmit(selectedOption!)} disabled={!selectedOption} style={{ width: '100%', padding: '0.875rem', fontSize: '1rem' }}>
          Submit Answer
        </button>
      )}

      {/* Result */}
      {showResult && answerResult && (
        <div>
          <div style={{ padding: '1rem', borderRadius: '8px', marginBottom: '1rem', background: answerResult.is_correct ? '#d1fae5' : '#fee2e2' }}>
            <p style={{ fontWeight: 600, fontSize: '1.05rem' }}>
              {answerResult.is_correct ? 'Correct!' : `Incorrect — Answer: ${answerResult.correct_option}`}
            </p>
          </div>
          <div style={{ background: '#f9fafb', padding: '1rem', borderRadius: '8px', marginBottom: '1rem' }}>
            <h4 style={{ marginBottom: '0.5rem', fontSize: '0.9rem' }}>Explanation</h4>
            <p style={{ fontSize: '0.9rem', lineHeight: 1.6 }}>{answerResult.explanation}</p>
            {answerResult.ocg_chapter_ref && (
              <p style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: '#6b7280' }}>OCG Reference: {answerResult.ocg_chapter_ref}</p>
            )}
            {answerResult.mastered && (
              <p style={{ marginTop: '0.5rem', color: '#10b981', fontWeight: 500, fontSize: '0.9rem' }}>
                Mastered! Next review in {answerResult.next_review_days} days.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
