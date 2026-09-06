'use client';

import {useEffect,useState} from 'react';
import PlayerGate from '@/components/PlayerGate';
import QuizNav from '@/components/QuizNav';
import {api,DashboardStats} from '@/lib/api';

export default function StatsPage(){
  const [stats,setStats]=useState<DashboardStats|null>(null);const [error,setError]=useState('');
  useEffect(()=>{api.stats.dashboard().then(setStats).catch(caught=>setError(caught instanceof Error?caught.message:'Unable to load statistics'));},[]);
  return <PlayerGate><div className="quiz-page"><QuizNav/><main id="main-content" className="quiz-content"><p className="kicker"><span>05</span> Learning record</p><div className="page-title-row compact-title"><h1>Statistics</h1></div>
    {error?<p role="alert" className="form-error">{error}</p>:!stats?<p>Loading statistics…</p>:<><div className="stat-grid"><div><strong>{stats.questions_mastered}</strong><span>Mastered</span></div><div><strong>{stats.questions_attempted}</strong><span>Attempted</span></div><div><strong>{stats.overall_recall_rate}%</strong><span>Recall</span></div><div><strong>{stats.study_streak}</strong><span>Day streak</span></div></div><div className="domain-bars">{stats.domains.map(domain=>{const percent=domain.total_questions?Math.round(domain.mastered/domain.total_questions*100):0;return <div key={domain.domain}><span>{domain.name}</span><div className="progress-track"><i style={{width:`${percent}%`}}/></div><strong>{percent}%</strong></div>;})}</div></>}
  </main></div></PlayerGate>;
}
