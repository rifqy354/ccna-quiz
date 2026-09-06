import {NextRequest,NextResponse} from 'next/server';
import {routeForHost} from '@/lib/host-routing';

export function middleware(request:NextRequest){
  const decision=routeForHost(request.headers.get('host')??'',request.nextUrl.pathname);
  if(!decision) return NextResponse.next();
  if(decision.kind==='redirect') return NextResponse.redirect(decision.destination);
  return NextResponse.rewrite(new URL(decision.destination,request.url));
}

export const config={
  matcher:['/((?!api|_next/static|_next/image|.*\\..*).*)'],
};
