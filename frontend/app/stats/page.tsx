'use client';
import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { api, DashboardStats } from '@/lib/api';
import NavBar from '@/components/NavBar';

export default function StatsPage() {
  const { token } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,setError] = useState('');

  useEffect(() => {
    if (!token) return;
    api.stats.dashboard(token).then(setStats).catch(e=>setError(e.message)).finally(() => setLoading(false));
  }, [token]);

  if (loading) return <div><NavBar /><div className="container page"><p>Loading...</p></div></div>;

  if (!stats) return <div><NavBar/><div className="container page"><p role="alert">{error || 'Unable to load statistics'}</p><button onClick={() => window.location.reload()}>Retry</button></div></div>;
  const s = stats;
  const recallRate = s.overall_recall_rate;

  return (
    <div>
      <NavBar />
      <div className="container page">
        <h1 style={{ marginBottom: '2rem' }}>Statistics</h1>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
          {[
            { label: 'Total Questions', value: s.total_questions },
            { label: 'Mastered', value: s.questions_mastered, color: '#10b981' },
            { label: 'Overall Recall', value: `${recallRate}%`, color: '#7c3aed' },
            { label: 'Study Streak', value: `${s.study_streak} days` },
          ].map(stat => (
            <div key={stat.label} className="card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: stat.color || '#111827' }}>{stat.value}</div>
              <div style={{ fontSize: '0.875rem', color: '#6b7280', marginTop: '0.25rem' }}>{stat.label}</div>
            </div>
          ))}
        </div>
        <h2 style={{ marginBottom: '1rem' }}>Domain Progress</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {s.domains.map(d => {
            const pct = d.total_questions > 0 ? Math.round(d.mastered / d.total_questions * 100) : 0;
            const attemptedPct = d.total_questions > 0 ? Math.round(d.attempted / d.total_questions * 100) : 0;
            return (
              <div key={d.domain} className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <strong>{d.name}</strong>
                  <span style={{ color: '#10b981', fontWeight: 600 }}>{pct}% mastered</span>
                </div>
                <div style={{ background: '#e5e7eb', height: '10px', borderRadius: '5px', overflow: 'hidden' }}>
                  <div style={{ background: '#10b981', height: '100%', width: `${pct}%`, transition: 'width 0.3s' }} />
                </div>
                <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: '4px' }}>
                  {d.mastered}/{d.total_questions} mastered · {attemptedPct}% attempted
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
