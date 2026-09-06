'use client';

import Link from 'next/link';
import {useEffect,useState} from 'react';
import {useParams} from 'next/navigation';
import PlayerGate from '@/components/PlayerGate';
import QuizNav from '@/components/QuizNav';
import {api,DomainDetail} from '@/lib/api';

export default function DomainDetailPage(){
  const domainId=Number(useParams().id);const [detail,setDetail]=useState<DomainDetail|null>(null);const [error,setError]=useState('');
  useEffect(()=>{if(!Number.isInteger(domainId)){setError('Invalid domain');return;}api.domains.get(domainId).then(setDetail).catch(caught=>setError(caught instanceof Error?caught.message:'Unable to load domain'));},[domainId]);
  return <PlayerGate><div className="quiz-page"><QuizNav/><main id="main-content" className="quiz-content"><Link className="text-link" href="/domains">← All domains</Link>
    {error?<p role="alert" className="form-error">{error}</p>:!detail?<p>Loading domain…</p>:<><p className="kicker domain-kicker"><span>{String(domainId).padStart(2,'0')}</span> Exam domain</p><h1 className="content-title">{detail.name}</h1><div className="topic-index">{detail.sub_domains.map(topic=><div key={topic.sub_domain}><strong>{topic.sub_domain}</strong><span>{topic.sub_domain_name||topic.sub_domain}</span><small>{topic.cnt} questions</small></div>)}</div><Link className="button-link" href={`/study?domain=${domainId}`}>Study this domain</Link></>}
  </main></div></PlayerGate>;
}
