import {expect,it} from 'vitest';
import {routeForHost} from '../lib/host-routing';

it('routes public apex and quiz paths to their internal trees',()=>{
  expect(routeForHost('email2.my.id','/')).toEqual({kind:'rewrite',destination:'/portfolio'});
  expect(routeForHost('email2.my.id','/writeups')).toEqual({kind:'rewrite',destination:'/portfolio/writeups'});
  expect(routeForHost('quiz.email2.my.id','/')).toEqual({kind:'rewrite',destination:'/quiz'});
  expect(routeForHost('quiz.email2.my.id','/domains/1')).toEqual({kind:'rewrite',destination:'/quiz/domains/1'});
});

it('redirects pages requested on the wrong public host',()=>{
  expect(routeForHost('email2.my.id','/challenge')).toEqual({kind:'redirect',destination:'https://quiz.email2.my.id/challenge'});
  expect(routeForHost('quiz.email2.my.id','/writeups')).toEqual({kind:'redirect',destination:'https://email2.my.id/writeups'});
});

it('supports local hostnames and ports',()=>{
  expect(routeForHost('localhost:3000','/')).toEqual({kind:'rewrite',destination:'/portfolio'});
  expect(routeForHost('quiz.localhost:3000','/leaderboard')).toEqual({kind:'rewrite',destination:'/quiz/leaderboard'});
});

it('leaves API, Next assets, and public files alone',()=>{
  expect(routeForHost('quiz.email2.my.id','/api/player/me')).toBeNull();
  expect(routeForHost('email2.my.id','/_next/static/app.js')).toBeNull();
  expect(routeForHost('email2.my.id','/favicon.ico')).toBeNull();
  expect(routeForHost('email2.my.id','/images/diagram.png')).toBeNull();
});

it('does not double-prefix internal route destinations',()=>{
  expect(routeForHost('email2.my.id','/portfolio/writeups')).toBeNull();
  expect(routeForHost('quiz.email2.my.id','/quiz/challenge')).toBeNull();
});
