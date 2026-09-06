'use client';

import Link from 'next/link';
import {useCallback,useState} from 'react';
import PlayerGate from '@/components/PlayerGate';
import QuizNav from '@/components/QuizNav';
import SessionRunner from '@/components/SessionRunner';
import {api,ChallengeSummary,SessionSummary,sessionCounts} from '@/lib/api';

export default function ChallengePage(){
  const [sessionId,setSessionId]=useState<number|null>(null);
  const [summary,setSummary]=useState<ChallengeSummary|null>(null);
  const [pending,setPending]=useState(false);
  const [error,setError]=useState('');
  const start=async()=>{
    if(pending) return;setPending(true);setError('');setSummary(null);
    try{const session=await api.sessions.challenge();sessionCounts.set(session.session_id,20);setSessionId(session.session_id);}catch(caught){setError(caught instanceof Error?caught.message:'Unable to start challenge');}finally{setPending(false);}
  };
  const finish=useCallback((result:SessionSummary)=>{
    if(sessionId!==null) sessionCounts.delete(sessionId);
    setSessionId(null);setSummary(result as ChallengeSummary);
  },[sessionId]);
  return <PlayerGate><div className="quiz-page"><QuizNav/><main id="main-content" className="quiz-content">
    {summary?<section className="challenge-result"><p className="kicker"><span>✓</span> Best on record</p><h1>Challenge complete</h1><div className="score-display">{summary.score}</div><div className="score-details"><span>{summary.correct_count} correct</span><span>{summary.wrong_count} wrong</span><span>Rank {summary.rank}</span></div><div className="action-row"><button onClick={start}>Try another challenge</button><Link className="button-link secondary-action" href="/leaderboard">View leaderboard</Link></div></section>:
    sessionId?<SessionRunner sessionId={sessionId} totalQuestions={20} mode="challenge" onComplete={finish}/>:
    <section className="challenge-intro"><p className="kicker"><span>03</span> Challenge mode</p><h1>20 questions.<br/>100 points.</h1><p>Three questions from each CCNA domain, plus two from the practice exams. Only your best completed score stays on the leaderboard.</p>{error&&<p role="alert" className="form-error">{error}</p>}<button className="primary-action" onClick={start} disabled={pending}>{pending?'Preparing challenge…':'Start 20-question challenge'}</button></section>}
  </main></div></PlayerGate>;
}
