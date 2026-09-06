'use client';

import {Suspense,useEffect,useState} from 'react';
import {useRouter,useSearchParams} from 'next/navigation';
import PlayerGate from '@/components/PlayerGate';
import QuizNav from '@/components/QuizNav';
import {api,DomainSummary,sessionCounts} from '@/lib/api';

function StudyForm(){
  const search=useSearchParams();const router=useRouter();
  const [domain,setDomain]=useState<number|''>(search.get('domain')?Number(search.get('domain')):'');
  const [sessionType,setSessionType]=useState<'mixed'|'review'|'new'>('mixed');const [count,setCount]=useState(20);
  const [domains,setDomains]=useState<DomainSummary[]>([]);const [pending,setPending]=useState(false);const [error,setError]=useState('');
  useEffect(()=>{api.domains.list().then(setDomains).catch(caught=>setError(caught instanceof Error?caught.message:'Unable to load domains'));},[]);
  const start=async()=>{if(pending)return;if(!Number.isInteger(count)||count<1||count>50){setError('Choose 1–50 questions');return;}setPending(true);setError('');try{const session=await api.sessions.start({domain:domain||undefined,session_type:sessionType,count});sessionCounts.set(session.session_id,session.total_questions);router.push(`/study/${session.session_id}`);}catch(caught){setError(caught instanceof Error?caught.message:'Unable to start session');}finally{setPending(false);}};
  return <section className="study-form"><p className="kicker"><span>02</span> Study session</p><h1>Build a question set.</h1><div className="form-grid">
    <label>Domain<select value={domain} onChange={event=>setDomain(event.target.value?Number(event.target.value):'')}><option value="">All domains</option>{domains.map(item=><option key={item.domain} value={item.domain}>{item.name}</option>)}</select></label>
    <label>Session type<select value={sessionType} onChange={event=>setSessionType(event.target.value as typeof sessionType)}><option value="mixed">Mixed — review and new</option><option value="review">Review — previously studied</option><option value="new">New questions only</option></select></label>
    <label>Questions (1–50)<input type="number" min={1} max={50} value={count} onChange={event=>setCount(Number(event.target.value))}/></label>
  </div>{error&&<p role="alert" className="form-error">{error}</p>}<button className="primary-action" onClick={start} disabled={pending}>{pending?'Building session…':'Start session'}</button></section>;
}

export default function StudyPage(){return <PlayerGate><div className="quiz-page"><QuizNav/><main id="main-content" className="quiz-content"><Suspense fallback={<p>Loading study options…</p>}><StudyForm/></Suspense></main></div></PlayerGate>;}
