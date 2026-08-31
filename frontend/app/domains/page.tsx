'use client';
import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { api, DomainSummary } from '@/lib/api';
import NavBar from '@/components/NavBar';

const DOMAIN_NAMES: Record<number, string> = {
  1: 'Network Fundamentals', 2: 'Network Access', 3: 'IP Connectivity',
  4: 'IP Services', 5: 'Security Fundamentals', 6: 'Automation and Programmability',
};

export default function DomainsPage() {
  const { token } = useAuth();
  const [domains, setDomains] = useState<DomainSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    api.domains.list(token).then(setDomains).finally(() => setLoading(false));
  }, [token]);

  return (
    <div>
      <NavBar />
      <div className="container page">
        <h1 style={{ marginBottom: '0.5rem' }}>CCNA Exam Domains</h1>
        <p style={{ color: '#6b7280', marginBottom: '2rem' }}>6 domains cover all CCNA 200-301 exam topics.</p>
        {loading ? <p>Loading...</p> : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
            {domains.map(d => {
              const pct = d.total_questions > 0 ? Math.round(d.mastered / d.total_questions * 100) : 0;
              const attemptedPct = d.total_questions > 0 ? Math.round(d.attempted / d.total_questions * 100) : 0;
              return (
                <div key={d.domain} className="card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <h3 style={{ fontSize: '0.95rem' }}>Domain {d.domain}</h3>
                    <a href={`/study?domain=${d.domain}`}><button style={{ padding: '0.25rem 0.75rem', fontSize: '0.875rem' }}>Study</button></a>
                  </div>
                  <p style={{ fontSize: '0.875rem', fontWeight: 600, color: '#374151' }}>{DOMAIN_NAMES[d.domain] || d.name}</p>
                  <div style={{ marginTop: '0.5rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#6b7280' }}>
                      <span>Mastery {pct}%</span><span>{d.mastered}/{d.total_questions}</span>
                    </div>
                    <div style={{ background: '#e5e7eb', height: '6px', borderRadius: '3px', marginTop: '4px' }}>
                      <div style={{ background: '#10b981', height: '100%', width: `${pct}%`, borderRadius: '3px', transition: 'width 0.3s' }} />
                    </div>
                    <div style={{ fontSize: '0.7rem', color: '#9ca3af', marginTop: '4px' }}>{attemptedPct}% attempted</div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
