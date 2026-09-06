'use client';
import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { api, DomainSummary, sessionCounts } from '@/lib/api';
import NavBar from '@/components/NavBar';

function StudyStartForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { token } = useAuth();
  const [domain, setDomain] = useState<number | ''>(searchParams.get('domain') ? Number(searchParams.get('domain')) : '');
  const [sessionType, setSessionType] = useState<'mixed' | 'review' | 'new'>('mixed');
  const [count, setCount] = useState(20);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [domains,setDomains] = useState<DomainSummary[]>([]);
  useEffect(() => { if(token) api.domains.list(token).then(setDomains).catch(e=>setError(e.message)); },[token]);

  const start = async () => {
    setLoading(true); setError('');
    try {
      if (!token) throw new Error('Please sign in first');
      if (!Number.isInteger(count) || count < 1 || count > 50) throw new Error('Choose 1-50 questions');
      const data = await api.sessions.start({domain: domain || undefined, session_type: sessionType, count},token);
      sessionCounts.set(data.session_id,data.total_questions);
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
              {domains.map(d => <option key={d.domain} value={d.domain}>{d.name}</option>)}
            </select></label>
            <label>Session Type<select value={sessionType} onChange={e => setSessionType(e.target.value as any)} style={{ marginTop: '0.25rem' }}>
              <option value="mixed">Mixed (Review + New)</option>
              <option value="review">Review Previously Studied Questions</option>
              <option value="new">New Questions Only</option>
            </select></label>
            <label>Questions (1-50)<input type="number" min={1} max={50} value={count} onChange={e => setCount(Number(e.target.value))} style={{ marginTop: '0.25rem' }} /></label>
            {error && <p style={{ color: '#dc2626' }}>{error}</p>}
            <button onClick={start} disabled={loading || !token} style={{ padding: '0.75rem', fontSize: '1rem' }}>
              {loading ? 'Starting...' : 'Start Session'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function StudyStartPage() { return <Suspense fallback={<p>Loading...</p>}><StudyStartForm /></Suspense>; }
