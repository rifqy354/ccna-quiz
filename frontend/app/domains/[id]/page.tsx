'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth-context';
import { api } from '@/lib/api';
import NavBar from '@/components/NavBar';

const DOMAIN_NAMES: Record<number, string> = {
  1: 'Network Fundamentals', 2: 'Network Access', 3: 'IP Connectivity',
  4: 'IP Services', 5: 'Security Fundamentals', 6: 'Automation and Programmability',
};

export default function DomainDetailPage() {
  const params = useParams();
  const domainId = Number(params.id);
  const { token } = useAuth();
  const [detail, setDetail] = useState<{ domain: number; name: string; sub_domains: any[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,setError] = useState('');

  useEffect(() => {
    if (!Number.isInteger(domainId)) { setError('Invalid domain'); setLoading(false); return; }
    if (!token) return;
    api.domains.get(domainId, token).then(setDetail).catch(e=>setError(e.message)).finally(() => setLoading(false));
  }, [token, domainId]);

  if (loading) return <div><NavBar /><div className="container page"><p>Loading...</p></div></div>;
  if (!detail) return <div><NavBar /><div className="container page"><p>{error || 'Domain not found.'}</p></div></div>;

  return (
    <div>
      <NavBar />
      <div className="container page">
        <Link href="/domains" style={{ fontSize: '0.875rem' }}>&larr; Back to all domains</Link>
        <h1 style={{ margin: '0.75rem 0 0.5rem' }}>Domain {domainId}: {DOMAIN_NAMES[domainId] || detail.name}</h1>
        {detail.sub_domains.length > 0 && (
          <>
            <h2 style={{ marginTop: '2rem', marginBottom: '1rem', fontSize: '1.1rem' }}>Sub-Topics</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {detail.sub_domains.map((sd: any) => (
                <div key={sd.sub_domain} className="card" style={{ padding: '0.75rem 1rem' }}>
                  <strong style={{ fontSize: '0.875rem' }}>{sd.sub_domain}</strong>
                  <span style={{ color: '#6b7280', marginLeft: '0.5rem' }}>{sd.sub_domain_name || sd.sub_domain}</span>
                  <span style={{ color: '#9ca3af', fontSize: '0.75rem', marginLeft: '0.5rem' }}>({sd.cnt} questions)</span>
                </div>
              ))}
            </div>
          </>
        )}
        <div style={{ marginTop: '2rem' }}>
          <Link href={`/study?domain=${domainId}`}>
            <button className="success">Study Domain {domainId}</button>
          </Link>
        </div>
      </div>
    </div>
  );
}
