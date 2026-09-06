'use client';

import {FormEvent,useRef,useState} from 'react';
import {usePlayer} from '@/lib/player-context';

export default function NamePrompt(){
  const {createPlayer,error}=usePlayer();
  const [name,setName]=useState('');
  const [pending,setPending]=useState(false);
  const pendingRef=useRef(false);

  const submit=async(event:FormEvent)=>{
    event.preventDefault();
    if(pendingRef.current) return;
    const cleaned=name.trim();
    if(cleaned.length<2||cleaned.length>24) return;
    pendingRef.current=true;setPending(true);
    try{await createPlayer(cleaned);}finally{pendingRef.current=false;setPending(false);}
  };

  return <main id="main-content" className="name-entry">
    <section className="name-card" aria-labelledby="player-name-title">
      <p className="kicker"><span>01</span> First visit</p>
      <h1 id="player-name-title">Choose your player name</h1>
      <p className="name-intro">Your best challenge score will be saved to this browser.</p>
      <form onSubmit={submit}>
        <label htmlFor="player-name">Your name</label>
        <input id="player-name" name="name" value={name} onChange={event=>setName(event.target.value)} minLength={2} maxLength={24} autoComplete="nickname" autoFocus/>
        <p className="field-note">2–24 characters. Duplicate names are allowed.</p>
        {error&&<p className="form-error" role="alert">{error}</p>}
        <button className="primary-action" type="submit" disabled={pending||name.trim().length<2}>
          {pending?'Creating player…':'Enter the quiz'}
        </button>
      </form>
    </section>
  </main>;
}
