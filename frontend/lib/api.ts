export const API_BASE=(process.env.NEXT_PUBLIC_API_URL||'').replace(/\/$/,'');
const credentialsMode:RequestCredentials=API_BASE?'include':'same-origin';

export class ApiError extends Error {
  constructor(public status:number,message:string){super(message);this.name='ApiError';}
}

function errorDetail(detail:unknown,status:number):string{
  if(Array.isArray(detail)) return detail.map((value:{msg?:string})=>value.msg||'Invalid input').join('; ');
  return typeof detail==='string'?detail:`Request failed (HTTP ${status})`;
}

type ApiInit={body?:object;method?:'GET'|'POST'};

export async function cookieFetch<T>(path:string,init:ApiInit={}):Promise<T>{
  const response=await fetch(`${API_BASE}${path}`,{
    method:init.method??(init.body?'POST':'GET'),
    credentials:credentialsMode,
    headers:{'Content-Type':'application/json'},
    ...(init.body?{body:JSON.stringify(init.body)}:{}),
  });
  if(!response.ok){
    const error=await response.json().catch(()=>({}));
    throw new ApiError(response.status,errorDetail(error.detail,response.status));
  }
  return response.status===204?null as T:response.json();
}

// Volatile display metadata only. Active session queues stay exclusively in backend memory.
export const sessionCounts=new Map<number,number>();

export interface Player{name:string}
export interface DomainSummary{domain:number;name:string;total_questions:number;mastered:number;attempted:number}
export interface DomainDetail{domain:number;name:string;sub_domains:Array<{sub_domain:string;sub_domain_name?:string;cnt:number}>}
export interface QuestionResponse{
  id:number;source_book:string;source_chapter:string;book_title:string;domain:number;
  sub_domain?:string;sub_domain_name?:string;question_text:string;question_image?:string;
  option_a:string;option_b:string;option_c:string;option_d:string;
  option_e?:string;option_f?:string;option_g?:string;is_multi_answer:boolean;
}
export interface AnswerData{
  question_id:number;selected_options:string[];confidence:'again'|'hard'|'good'|'easy';response_time_ms?:number;
}
export interface AnswerResponse{
  is_correct:boolean;correct_option:string;user_selection:string;explanation:string;
  ocg_chapter_ref?:string;ocg_section_ref?:string;mastered:boolean;next_review_days:number;
}
export interface SessionStartResponse{session_id:number;total_questions:number;session_type:string}
export interface SessionSummary{
  session_id:number;questions_shown:number;correct_count:number;accuracy_pct:number;completed_at:string;
  score?:number;wrong_count?:number;rank?:number;
}
export interface ChallengeSummary extends SessionSummary{score:number;wrong_count:number;rank:number}
export interface LeaderboardEntry{rank:number;name:string;score:number;correct:number;wrong:number}
export interface DashboardStats{
  total_questions:number;questions_mastered:number;questions_attempted:number;
  overall_recall_rate:number;study_streak:number;due_today:number;domains:DomainSummary[];
}

export const api={
  player:{
    create:(name:string)=>cookieFetch<Player>('/api/player',{body:{name}}),
    me:()=>cookieFetch<Player>('/api/player/me'),
  },
  domains:{
    list:()=>cookieFetch<DomainSummary[]>('/api/domains'),
    get:(domain:number)=>cookieFetch<DomainDetail>(`/api/domains/${domain}`),
  },
  sessions:{
    challenge:()=>cookieFetch<SessionStartResponse>('/api/sessions/challenge',{method:'POST'}),
    start:(data:{domain?:number;session_type:'mixed'|'new'|'review';count:number})=>cookieFetch<SessionStartResponse>('/api/sessions/start',{body:data}),
    next:(sessionId:number)=>cookieFetch<QuestionResponse|null>(`/api/sessions/${sessionId}/next`),
    answer:(sessionId:number,data:AnswerData)=>cookieFetch<AnswerResponse>(`/api/sessions/${sessionId}/answer`,{body:data}),
    complete:(sessionId:number)=>cookieFetch<SessionSummary>(`/api/sessions/${sessionId}/complete`,{method:'POST'}),
  },
  stats:{dashboard:()=>cookieFetch<DashboardStats>('/api/stats/dashboard')},
  leaderboard:{list:()=>cookieFetch<LeaderboardEntry[]>('/api/leaderboard')},
};
