import {cleanup,fireEvent,render,screen} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';

const mocks=vi.hoisted(()=>({challenge:vi.fn()}));
vi.mock('../lib/player-context',()=>({usePlayer:()=>({player:{name:'Rifqy'},loading:false,error:null})}));
vi.mock('../lib/api',()=>({api:{sessions:{challenge:mocks.challenge}},sessionCounts:new Map()}));
vi.mock('../components/SessionRunner',()=>({default:({onComplete}:{onComplete:(summary:object)=>void})=><button onClick={()=>onComplete({session_id:7,questions_shown:20,correct_count:17,accuracy_pct:85,completed_at:'2026-09-06T00:00:00Z',score:85,wrong_count:3,rank:4})}>Finish mocked challenge</button>}));

import ChallengePage from '../app/quiz/challenge/page';

beforeEach(()=>mocks.challenge.mockResolvedValue({session_id:7,total_questions:20,session_type:'challenge'}));
afterEach(cleanup);

it('starts a fixed challenge and renders backend result values',async()=>{
  render(<ChallengePage/>);
  fireEvent.click(screen.getByRole('button',{name:'Start 20-question challenge'}));
  expect(await screen.findByText('Finish mocked challenge')).toBeTruthy();
  expect(mocks.challenge).toHaveBeenCalledWith();
  fireEvent.click(screen.getByText('Finish mocked challenge'));
  expect(await screen.findByText('85')).toBeTruthy();
  expect(screen.getByText('17 correct')).toBeTruthy();
  expect(screen.getByText('3 wrong')).toBeTruthy();
  expect(screen.getByText('Rank 4')).toBeTruthy();
  expect(screen.getByRole('link',{name:'View leaderboard'})).toBeTruthy();
});
