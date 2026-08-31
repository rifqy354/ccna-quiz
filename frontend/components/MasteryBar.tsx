'use client';
import { DomainSummary } from '@/lib/api';

const DOMAIN_NAMES: Record<number, string> = {
  1: 'Network Fundamentals', 2: 'Network Access', 3: 'IP Connectivity',
  4: 'IP Services', 5: 'Security Fundamentals', 6: 'Automation and Programmability',
};

interface MasteryBarProps {
  domains: DomainSummary[];
}

export default function MasteryBar({ domains }: MasteryBarProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {domains.map(d => {
        const pct = d.total_questions > 0 ? Math.round(d.mastered / d.total_questions * 100) : 0;
        const attemptedPct = d.total_questions > 0 ? Math.round(d.attempted / d.total_questions * 100) : 0;
        return (
          <div key={d.domain}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.375rem' }}>
              <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>{d.name}</span>
              <span style={{ fontSize: '0.875rem', color: '#10b981', fontWeight: 600 }}>{pct}%</span>
            </div>
            <div style={{ background: '#e5e7eb', height: '10px', borderRadius: '5px', overflow: 'hidden' }}>
              <div style={{ background: '#10b981', height: '100%', width: `${pct}%`, transition: 'width 0.3s' }} />
            </div>
            <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: '2px' }}>
              {d.mastered}/{d.total_questions} mastered · {attemptedPct}% attempted
            </div>
          </div>
        );
      })}
    </div>
  );
}
