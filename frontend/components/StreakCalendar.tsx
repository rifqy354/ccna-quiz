'use client';

interface StreakCalendarProps {
  streak: number;
}

export default function StreakCalendar({ streak }: StreakCalendarProps) {
  return (
    <div>
      <p style={{ marginTop: '0.75rem', fontWeight: 600, fontSize: '0.9rem' }}>
        {streak}-day streak {streak >= 7 ? '🔥' : ''}
      </p>
      <p style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: '0.25rem' }}>
        Study every day to build your streak!
      </p>
    </div>
  );
}
