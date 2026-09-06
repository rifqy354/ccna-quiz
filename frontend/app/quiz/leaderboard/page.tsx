'use client';

import {useCallback,useEffect,useState} from 'react';
import LeaderboardTable from '@/components/LeaderboardTable';
import QuizNav from '@/components/QuizNav';
import {api,LeaderboardEntry} from '@/lib/api';

export default function LeaderboardPage(){
  const [entries,setEntries]=useState<LeaderboardEntry[]|null>(null);
  const [error,setError]=useState('');
  const load=useCallback(async()=>{setError('');try{setEntries(await api.leaderboard.list());}catch(caught){setEntries(null);setError(caught instanceof Error?caught.message:'Unable to load leaderboard');}},[]);
  useEffect(()=>{void load();},[load]);
  return <div className="quiz-page"><QuizNav/><main id="main-content" className="quiz-content"><section className="leaderboard-page"><p className="kicker"><span>04</span> Public records</p><div className="page-title-row"><h1>Leaderboard</h1><p className="section-count">Best score only</p></div>
    {error?<div className="runner-state"><p role="alert">{error}</p><button onClick={load}>Retry</button></div>:entries===null?<p>Loading leaderboard…</p>:entries.length===0?<p className="empty-table">No completed challenges yet.</p>:<LeaderboardTable entries={entries}/>}
  </section></main></div>;
}
