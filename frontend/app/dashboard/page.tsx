'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth-context';
import { api, DashboardStats } from '@/lib/api';
import NavBar from '@/components/NavBar';

const DOMAIN_NAMES: Record<number, string> = {
  1: 'Network Fundamentals', 2: 'Network Access', 3: 'IP Connectivity',
  4: 'IP Services', 5: 'Security Fundamentals', 6: 'Automation and Programmability',
};

export default function DashboardPage() {
  const { user, token, loading: authLoading } = useAuth();
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !user) { router.push('/login'); return; }
    if (!token) return;
    api.stats.dashboard(token).then(setStats).finally(() => setLoading(false));
  }, [user, token, authLoading, router]);

  if (authLoading || loading) return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
      <p style={{ color: '#6b7280' }}>Loading dashboard...</p>
    </div>
  );

  const s = stats!;

  return (
    <div>
      <NavBar />
      <div className="container page">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
          <div>
            <h1 style={{ fontSize: '1.75rem' }}>Welcome back, {user?.name}!</h1>
            <p style={{ color: '#6b7280', marginTop: '0.25rem' }}>
              {s.questions_mastered} questions mastered · {s.due_today > 0 ? `${s.due_today} due for review` : 'All caught up!'}
            </p>
          </div>
          <Link href="/study">
            <button className="success" style={{ padding: '0.75rem 1.5rem', fontSize: '1rem' }}>
              {s.due_today > 0 ? `Study (${s.due_today} due)` : 'Start Session'}
            </button>
          </Link>
        </div>

        {/* Stat cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
          {[
            { label: 'Mastered', value: s.questions_mastered, color: '#10b981' },
            { label: 'Attempted', value: s.questions_attempted, color: '#3b82f6' },
            { label: 'Recall Rate', value: `${s.overall_recall_rate}%`, color: '#7c3aed' },
            { label: 'Study Streak', value: `${s.study_streak} days`, color: '#f59e0b' },
          ].map(stat => (
            <div key={stat.label} className="card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: stat.color }}>{stat.value}</div>
              <div style={{ fontSize: '0.8rem', color: '#6b7280', marginTop: '0.25rem' }}>{stat.label}</div>
            </div>
          ))}
        </div>

        {/* Domain mastery */}
        <h2 style={{ marginBottom: '1rem' }}>Domain Mastery</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '2rem' }}>
          {s.domains.map(d => {
            const pct = d.total_questions > 0 ? Math.round(d.mastered / d.total_questions * 100) : 0;
            const attemptedPct = d.total_questions > 0 ? Math.round(d.attempted / d.total_questions * 100) : 0;
            return (
              <div key={d.domain} className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span style={{ fontWeight: 500 }}>{d.name}</span>
                  <span style={{ color: '#10b981', fontWeight: 600 }}>{pct}%</span>
                </div>
                <div style={{ background: '#e5e7eb', height: '10px', borderRadius: '5px', overflow: 'hidden' }}>
                  <div style={{ background: '#10b981', height: '100%', width: `${pct}%`, transition: 'width 0.3s' }} />
                </div>
                <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: '4px' }}>
                  {d.mastered}/{d.total_questions} mastered · {d.attempted} attempted
                </div>
              </div>
            );
          })}
        </div>

        {/* Quick links */}
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <Link href="/domains"><button className="secondary">Browse Domains</button></Link>
          <Link href="/stats"><button className="secondary">View Stats</button></Link>
        </div>
      </div>
    </div>
  );
}
