import {cleanup,render,screen} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';

const playerState=vi.hoisted(()=>({player:null as null|{name:string},loading:false,error:null as string|null,createPlayer:vi.fn(),refreshPlayer:vi.fn(),clearPlayer:vi.fn()}));
vi.mock('../lib/player-context',()=>({usePlayer:()=>playerState}));
vi.mock('../lib/api',()=>({api:{stats:{dashboard:vi.fn()}}}));

import QuizHome from '../app/quiz/page';

afterEach(()=>{cleanup();playerState.player=null;playerState.loading=false;playerState.error=null;});

it('shows only the name entry experience to a first-time visitor',()=>{
  render(<QuizHome/>);
  expect(screen.getByRole('heading',{name:'Choose your player name'})).toBeTruthy();
  expect(screen.getByLabelText('Your name')).toBeTruthy();
  expect(screen.queryByText('Domain study')).toBeNull();
  expect(screen.queryByText(/login|register|password|email|logout/i)).toBeNull();
});

it('shows study, challenge, leaderboard, and portfolio navigation to a returning player',()=>{
  playerState.player={name:'Rifqy'};
  render(<QuizHome/>);
  expect(screen.getAllByText('Rifqy')).toHaveLength(2);
  expect(screen.getByRole('link',{name:/Domain study/})).toBeTruthy();
  expect(screen.getByRole('link',{name:'Challenge'})).toBeTruthy();
  expect(screen.getByRole('link',{name:'Leaderboard'})).toBeTruthy();
  expect(screen.getByRole('link',{name:'Portfolio ↗'}).getAttribute('href')).toBe('https://email2.my.id/');
});
