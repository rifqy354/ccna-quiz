'use client';

import {ReactNode} from 'react';
import NamePrompt from './NamePrompt';
import {usePlayer} from '@/lib/player-context';

export default function PlayerGate({children}:{children:ReactNode}){
  const {player,loading,error,refreshPlayer}=usePlayer();
  if(loading) return <main className="center-state"><p>Finding your player record…</p></main>;
  if(!player){
    if(error) return <main className="center-state"><p role="alert">{error}</p><button onClick={refreshPlayer}>Retry</button></main>;
    return <NamePrompt/>;
  }
  return <>{children}</>;
}
