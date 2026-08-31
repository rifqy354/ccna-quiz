'use client';
import Link from 'next/link';

interface DomainCardProps {
  domain: number;
  name: string;
  total: number;
  mastered: number;
  attempted: number;
}

export default function DomainCard({ domain, name, total, mastered, attempted }: DomainCardProps) {
  const pct = total > 0 ? Math.round(mastered / total * 100) : 0;
  const attemptedPct = total > 0 ? Math.round(attempted / total * 100) : 0;

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginBottom: '0.25rem' }}>Domain {domain}</div>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>{name}</h3>
        </div>
        <span style={{ fontSize: '1.5rem', fontWeight: 700, color: '#10b981' }}>{pct}%</span>
      </div>
      <div style={{ background: '#e5e7eb', height: '6px', borderRadius: '3px', overflow: 'hidden' }}>
        <div style={{ background: '#10b981', height: '100%', width: `${pct}%`, transition: 'width 0.3s' }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#6b7280' }}>
        <span>{mastered}/{total} mastered</span>
        <span>{attemptedPct}% attempted</span>
      </div>
      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.25rem' }}>
        <Link href={`/study?domain=${domain}`} style={{ flex: 1 }}>
          <button style={{ width: '100%', padding: '0.375rem', fontSize: '0.875rem' }}>Study</button>
        </Link>
        <Link href={`/domains/${domain}`} style={{ flex: 1 }}>
          <button className="secondary" style={{ width: '100%', padding: '0.375rem', fontSize: '0.875rem' }}>Details</button>
        </Link>
      </div>
    </div>
  );
}
