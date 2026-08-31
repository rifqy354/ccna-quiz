'use client';
import { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import NavBar from '@/components/NavBar';

export default function StudyStartPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { token } = useAuth();
  const [domain, setDomain] = useState<number | ''>(searchParams.get('domain') ? Number(searchParams.get('domain')) : '');
  const [sessionType, setSessionType] = useState<'mixed' | 'review' | 'new'>('mixed');
  const [count, setCount] = useState(20);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const start = async () => {
    setLoading(true); setError('');
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/sessions/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ domain: domain || undefined, session_type: sessionType, count }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || 'Failed');
      const data = await res.json();
      sessionStorage.setItem(`session_${data.session_id}_count`, String(data.total_questions));
      router.push(`/study/${data.session_id}`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <NavBar />
      <div className="container page">
        <div className="card" style={{ maxWidth: '500px', margin: '0 auto' }}>
          <h1 style={{ marginBottom: '1.5rem' }}>Start Study Session</h1>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <label>Domain<select value={domain} onChange={e => setDomain(e.target.value ? Number(e.target.value) : '')} style={{ marginTop: '0.25rem' }}>
              <option value="">All Domains</option>
              {[1,2,3,4,5,6].map(d => <option key={d} value={d}>Domain {d}</option>)}
            </select></label>
            <label>Session Type<select value={sessionType} onChange={e => setSessionType(e.target.value as any)} style={{ marginTop: '0.25rem' }}>
              <option value="mixed">Mixed (Review + New)</option>
              <option value="review">Review Only (Due Questions)</option>
              <option value="new">New Questions Only</option>
            </select></label>
            <label>Questions (1-100)<input type="number" min={1} max={100} value={count} onChange={e => setCount(Number(e.target.value))} style={{ marginTop: '0.25rem' }} /></label>
            {error && <p style={{ color: '#dc2626' }}>{error}</p>}
            <button onClick={start} disabled={loading} style={{ padding: '0.75rem', fontSize: '1rem' }}>
              {loading ? 'Starting...' : 'Start Session'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
