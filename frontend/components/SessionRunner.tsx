'use client';

import Link from 'next/link';
import {useCallback,useEffect,useRef,useState} from 'react';
import {api,API_BASE,AnswerResponse,QuestionResponse,SessionSummary} from '@/lib/api';

type Confidence='again'|'hard'|'good'|'easy';
type Phase='loading'|'question'|'result'|'done'|'error';

function optionEntries(question:QuestionResponse):Array<[string,string]>{
  return (['A','B','C','D','E','F','G'] as const).flatMap(letter=>{
    const value=question[`option_${letter.toLowerCase()}` as keyof QuestionResponse];
    return typeof value==='string'&&value?[[letter,value] as [string,string]]:[];
  });
}

interface SessionRunnerProps{
  sessionId:number;totalQuestions?:number;mode:'study'|'challenge';
  onComplete?:(summary:SessionSummary)=>void;
}

export default function SessionRunner({sessionId,totalQuestions,mode,onComplete}:SessionRunnerProps){
  const [phase,setPhase]=useState<Phase>('loading');
  const [question,setQuestion]=useState<QuestionResponse|null>(null);
  const [questionNumber,setQuestionNumber]=useState(1);
  const [selected,setSelected]=useState<Set<string>>(new Set());
  const [answer,setAnswer]=useState<AnswerResponse|null>(null);
  const [summary,setSummary]=useState<SessionSummary|null>(null);
  const [message,setMessage]=useState('');
  const [busy,setBusy]=useState(false);
  const busyRef=useRef(false);
  const startedAt=useRef(Date.now());

  const fail=(caught:unknown)=>{
    const raw=caught instanceof Error?caught.message:'Request failed';
    setMessage(/session not found/i.test(raw)?'This session expired when the quiz service restarted.':raw);
    setPhase('error');
  };

  const complete=useCallback(async()=>{
    const result=await api.sessions.complete(sessionId);
    setSummary(result);setPhase('done');onComplete?.(result);
  },[onComplete,sessionId]);

  const loadQuestion=useCallback(async()=>{
    const next=await api.sessions.next(sessionId);
    if(!next){await complete();return;}
    setQuestion(next);setSelected(new Set());setAnswer(null);setPhase('question');startedAt.current=Date.now();
  },[complete,sessionId]);

  const run=async(action:()=>Promise<void>)=>{
    if(busyRef.current) return;
    busyRef.current=true;setBusy(true);setMessage('');
    try{await action();}catch(caught){fail(caught);}finally{busyRef.current=false;setBusy(false);}
  };

  useEffect(()=>{void run(loadQuestion);},[loadQuestion]);

  const toggle=(letter:string)=>{
    if(phase!=='question'||busyRef.current||!question) return;
    setSelected(previous=>{
      if(!question.is_multi_answer) return new Set([letter]);
      const next=new Set(previous);next.has(letter)?next.delete(letter):next.add(letter);return next;
    });
  };

  const submit=(confidence:Confidence)=>run(async()=>{
    if(!question||selected.size===0||phase!=='question') return;
    try{
      const result=await api.sessions.answer(sessionId,{
        question_id:question.id,selected_options:Array.from(selected),confidence,
        response_time_ms:Date.now()-startedAt.current,
      });
      setAnswer(result);setPhase('result');
    }catch(caught){
      const raw=caught instanceof Error?caught.message:'Request failed';
      setMessage(raw);
    }
  });

  const next=()=>run(async()=>{setQuestionNumber(value=>value+1);await loadQuestion();});

  if(phase==='loading') return <div className="runner-state"><p>Loading question…</p></div>;
  if(phase==='error') return <div className="runner-state"><p role="alert">{message}</p><div className="action-row"><button onClick={()=>run(loadQuestion)} disabled={busy}>Retry</button><Link className="button-link secondary-action" href="/study">Start a new session</Link></div></div>;
  if(phase==='done'&&summary) return <section className="session-result"><p className="kicker"><span>✓</span> Complete</p><h1>Session complete</h1><p className="result-fraction">{summary.correct_count}<span> / {summary.questions_shown}</span></p><p>{summary.accuracy_pct}% correct</p><Link className="button-link" href="/study">Start another session</Link></section>;
  if(!question) return null;

  const progressTotal=totalQuestions??null;
  const correctLetters=answer?.correct_option.split('')??[];
  const userLetters=answer?.user_selection.split('')??[];
  return <section className="session-runner" aria-live="polite">
    <div className="question-meta"><span>Question {questionNumber}{progressTotal?` / ${progressTotal}`:''}</span><span>{question.book_title}</span></div>
    <div className="progress-track"><span style={{width:progressTotal?`${Math.min(100,questionNumber/progressTotal*100)}%`:'0%'}}/></div>
    {question.is_multi_answer&&phase==='question'&&<p className="multi-note">Select every correct answer.</p>}
    <div className="question-copy"><p>{question.question_text}</p>{question.question_image&&<img src={`${API_BASE}/api/images/${encodeURIComponent(question.question_image.split('/').pop()!)}`} alt="Question diagram"/>}</div>
    <div className="answer-list">{optionEntries(question).map(([letter,text])=>{
      const chosen=selected.has(letter);const correct=correctLetters.includes(letter);const wrong=phase==='result'&&userLetters.includes(letter)&&!correct;
      return <button key={letter} type="button" className={`answer-option ${chosen?'selected':''} ${phase==='result'&&correct?'correct':''} ${wrong?'wrong':''}`} onClick={()=>toggle(letter)} disabled={busy||phase==='result'}>
        <span className="answer-letter">{question.is_multi_answer?(chosen?'☑':'☐'):letter}</span><span>{text}</span>{phase==='result'&&correct&&<span className="answer-status">Correct</span>}{wrong&&<span className="answer-status">Wrong</span>}
      </button>;
    })}</div>
    {phase==='question'&&<div className="confidence-panel"><p>Submit with confidence</p><div className="confidence-grid">{(['again','hard','good','easy'] as Confidence[]).map(value=><button key={value} onClick={()=>submit(value)} disabled={busy||selected.size===0}>{value[0].toUpperCase()+value.slice(1)}</button>)}</div></div>}
    {phase==='result'&&answer&&<div className={`answer-explanation ${answer.is_correct?'is-correct':'is-wrong'}`}>
      <strong>{answer.is_correct?'Correct':'Incorrect'}</strong>
      <p>Your answer: {userLetters.join(', ')} · Correct answer: {correctLetters.join(', ')}</p>
      <h2>Explanation</h2><p>{answer.explanation}</p>
      {answer.ocg_chapter_ref&&<p className="reference">OCG Chapter {answer.ocg_chapter_ref}</p>}
      <button onClick={next} disabled={busy}>{progressTotal&&questionNumber>=progressTotal?'Finish':'Next question'}</button>
    </div>}
    {message&&<p className="form-error" role="alert">{message}</p>}
  </section>;
}
