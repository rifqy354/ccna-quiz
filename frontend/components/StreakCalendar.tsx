'use client';

interface StreakCalendarProps {
  streak: number;
}

export default function StreakCalendar({ streak }: StreakCalendarProps) {
  // 12 weeks of activity
  const weeks = 12;
  const cells = weeks * 7;

  return (
    <div>
      <div style={{ display: 'flex', gap: '3px', flexWrap: 'wrap', maxWidth: '200px' }}>
        {Array.from({ length: cells }).map((_, i) => (
          <div
            key={i}
            style={{
              width: '14px', height: '14px', borderRadius: '3px',
              background: '#d1fae5', border: '1px solid #6ee7b7',
              opacity: Math.random() > 0.5 ? 1 : 0.4,
            }}
            title={`Day ${i + 1}`}
          />
        ))}
      </div>
      <p style={{ marginTop: '0.75rem', fontWeight: 600, fontSize: '0.9rem' }}>
        {streak}-day streak {streak >= 7 ? '🔥' : ''}
      </p>
      <p style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: '0.25rem' }}>
        Study every day to build your streak!
      </p>
    </div>
  );
}
