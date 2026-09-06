'use client';

import Link from 'next/link';
import {usePlayer} from '@/lib/player-context';

export default function QuizNav(){
  const {player}=usePlayer();
  return <>
    <a className="skip-link" href="#main-content">Skip to content</a>
    <header className="quiz-header">
      <Link className="quiz-mark" href="/">CCNA / QUIZ</Link>
      <nav className="quiz-nav" aria-label="Quiz">
        <Link href="/domains">Domains</Link><Link href="/study">Study</Link>
        <Link href="/challenge">Challenge</Link><Link href="/leaderboard">Leaderboard</Link>
      </nav>
      <div className="player-mark"><span className="status-dot" aria-hidden="true"/>{player?.name??'Guest'}</div>
    </header>
  </>;
}
