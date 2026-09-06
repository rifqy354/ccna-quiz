export type HostRoute={kind:'rewrite'|'redirect';destination:string};

const QUIZ_PATHS=['/domains','/study','/stats','/challenge','/leaderboard'];

function hostname(host:string):string{
  return host.trim().toLowerCase().replace(/:\d+$/,'');
}

function isAsset(pathname:string):boolean{
  return pathname==='/api'||pathname.startsWith('/api/')||pathname==='/health'||
    pathname.startsWith('/_next/')||/\/[^/]+\.[^/]+$/.test(pathname);
}

function isQuizPath(pathname:string):boolean{
  return QUIZ_PATHS.some(prefix=>pathname===prefix||pathname.startsWith(`${prefix}/`));
}

export function routeForHost(host:string,pathname:string):HostRoute|null{
  if(isAsset(pathname)||pathname==='/portfolio'||pathname.startsWith('/portfolio/')||
    pathname==='/quiz'||pathname.startsWith('/quiz/')) return null;

  const currentHost=hostname(host);
  const apex=currentHost==='email2.my.id'||currentHost==='localhost'||currentHost==='127.0.0.1';
  const quiz=currentHost==='quiz.email2.my.id'||currentHost==='quiz.localhost';

  if(apex){
    if(pathname==='/') return {kind:'rewrite',destination:'/portfolio'};
    if(pathname==='/writeups'||pathname.startsWith('/writeups/')){
      return {kind:'rewrite',destination:`/portfolio${pathname}`};
    }
    if(isQuizPath(pathname)){
      const destination=currentHost==='localhost'
        ?`http://quiz.localhost${host.endsWith(':3000')?':3000':''}${pathname}`
        :`https://quiz.email2.my.id${pathname}`;
      return {kind:'redirect',destination};
    }
    return null;
  }

  if(quiz){
    if(pathname==='/writeups'||pathname.startsWith('/writeups/')){
      const destination=currentHost==='quiz.localhost'
        ?`http://localhost${host.endsWith(':3000')?':3000':''}${pathname}`
        :`https://email2.my.id${pathname}`;
      return {kind:'redirect',destination};
    }
    return {kind:'rewrite',destination:pathname==='/'?'/quiz':`/quiz${pathname}`};
  }

  return null;
}
