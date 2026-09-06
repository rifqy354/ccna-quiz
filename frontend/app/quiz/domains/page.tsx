'use client';

import Link from 'next/link';
import {useEffect,useState} from 'react';
import PlayerGate from '@/components/PlayerGate';
import QuizNav from '@/components/QuizNav';
import {api,DomainSummary} from '@/lib/api';

export default function DomainsPage(){
  const [domains,setDomains]=useState<DomainSummary[]>([]);const [loading,setLoading]=useState(true);const [error,setError]=useState('');
  useEffect(()=>{api.domains.list().then(setDomains).catch(caught=>setError(caught instanceof Error?caught.message:'Unable to load domains')).finally(()=>setLoading(false));},[]);
  return <PlayerGate><div className="quiz-page"><QuizNav/><main id="main-content" className="quiz-content"><p className="kicker"><span>01</span> Question bank</p><div className="page-title-row compact-title"><h1>Domains</h1><p className="section-count">CCNA 200-301</p></div>
    {error?<p role="alert" className="form-error">{error}</p>:loading?<p>Loading domains…</p>:<ol className="domain-index">{domains.map(domain=>{const mastery=domain.total_questions?Math.round(domain.mastered/domain.total_questions*100):0;return <li key={domain.domain}><Link href={`/domains/${domain.domain}`}><span className="domain-number">{String(domain.domain).padStart(2,'0')}</span><span><strong>{domain.name}</strong><small>{domain.total_questions} questions · {domain.attempted} attempted</small></span><span className="domain-mastery">{mastery}%<small>mastered</small></span></Link></li>;})}</ol>}
  </main></div></PlayerGate>;
}
