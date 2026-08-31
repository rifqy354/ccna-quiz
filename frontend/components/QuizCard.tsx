\
'use client';
import { useState } from 'react';
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

const OPTIONS = [
  { key: 'A', label: 'A' },
  { key: 'B', label: 'B' },
  { key: 'C', label: 'C' },
  { key: 'D', label: 'D' },
] as const;

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
    if (wrong) return { background: '#fee2e2', borderColor: '#ef4444', opacity: 0.6 };
    return { background: 'white', opacity: 0.5 };
  };

  const optionMap: Record<string, string> = {
    A: question.option_a, B: question.option_b, C: question.option_c, D: question.option_d,
  };

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
        {OPTIONS.map(({ key }) => (
          <button
            key={key}
            onClick={() => !showResult && onOptionChange(key)}
            disabled={showResult}
            style={{
              display: 'flex', gap: '0.75rem', padding: '0.875rem 1rem',
              textAlign: 'left', border: '2px solid #d1d5db', borderRadius: '8px',
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
