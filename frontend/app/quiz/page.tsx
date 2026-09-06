'use client';

import Link from 'next/link';
import NamePrompt from '@/components/NamePrompt';
import QuizNav from '@/components/QuizNav';
import {usePlayer} from '@/lib/player-context';

const modes=[
  {index:'01',title:'Domain study',description:'Choose a CCNA domain and build recall over time.',href:'/domains'},
  {index:'02',title:'Quick study',description:'Mix new and review questions into a focused session.',href:'/study'},
  {index:'03',title:'Challenge',description:'Twenty fixed questions. Five points for every correct answer.',href:'/challenge'},
  {index:'04',title:'Leaderboard',description:'Best public challenge records, ranked by score.',href:'/leaderboard'},
];

export default function QuizHome(){
  const {player,loading,error,refreshPlayer}=usePlayer();
  if(loading) return <main className="center-state"><p>Finding your player record…</p></main>;
  if(!player){
    if(error) return <main className="center-state"><p role="alert">{error}</p><button onClick={refreshPlayer}>Retry</button></main>;
    return <NamePrompt/>;
  }
  return <div className="quiz-page"><QuizNav/><main id="main-content">
    <section className="quiz-hero"><p className="kicker"><span>00</span> Player record</p><div className="quiz-hero-grid"><h1>Study the network.</h1><div><p className="player-label">Current player</p><p className="player-name">{player.name}</p><p>Practice the CCNA question bank or put a score on the board.</p></div></div></section>
    <section className="mode-section" aria-labelledby="quiz-modes"><div className="section-heading"><p className="kicker"><span>01</span> Choose a mode</p><a className="text-link" href="https://email2.my.id/">Portfolio ↗</a></div><h2 id="quiz-modes" className="sr-only">Quiz modes</h2>
      <ol className="mode-index">{modes.map(mode=><li key={mode.index}><Link href={mode.href}><span>{mode.index}</span><strong>{mode.title}</strong><small>{mode.description}</small><b aria-hidden="true">→</b></Link></li>)}</ol>
    </section>
  </main><footer className="site-footer"><a href="https://email2.my.id/writeups">CTF Writeups ↗</a><span>CCNA 200-301</span></footer></div>;
}
