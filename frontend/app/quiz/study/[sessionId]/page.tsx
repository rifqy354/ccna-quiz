'use client';

import {useParams} from 'next/navigation';
import PlayerGate from '@/components/PlayerGate';
import QuizNav from '@/components/QuizNav';
import SessionRunner from '@/components/SessionRunner';
import {sessionCounts} from '@/lib/api';

export default function SessionPage(){
  const sessionId=Number(useParams().sessionId);
  return <PlayerGate><div className="quiz-page"><QuizNav/><main id="main-content" className="quiz-content"><SessionRunner sessionId={sessionId} totalQuestions={sessionCounts.get(sessionId)} mode="study"/></main></div></PlayerGate>;
}
