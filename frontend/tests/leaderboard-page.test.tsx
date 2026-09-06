import {cleanup,fireEvent,render,screen} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';

const list=vi.hoisted(()=>vi.fn());
vi.mock('../lib/api',()=>({api:{leaderboard:{list}}}));
vi.mock('../components/QuizNav',()=>({default:()=>null}));

import LeaderboardPage from '../app/quiz/leaderboard/page';

beforeEach(()=>list.mockReset());
afterEach(cleanup);

it('renders only the approved leaderboard columns and tied ranks',async()=>{
  list.mockResolvedValue([{rank:1,name:'Ace',score:100,correct:20,wrong:0},{rank:2,name:'First Twin',score:90,correct:18,wrong:2},{rank:2,name:'Second Twin',score:90,correct:18,wrong:2}]);
  render(<LeaderboardPage/>);
  for(const heading of ['Rank','Name','Score','Correct','Wrong']) expect(await screen.findByRole('columnheader',{name:heading})).toBeTruthy();
  expect(screen.getAllByText('2')).toHaveLength(4);
  expect(screen.queryByText(/email|player id|completed/i)).toBeNull();
});

it('offers a working retry when leaderboard loading fails',async()=>{
  list.mockRejectedValueOnce(new Error('Leaderboard unavailable')).mockResolvedValueOnce([]);
  render(<LeaderboardPage/>);
  expect(await screen.findByRole('alert')).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Retry'}));
  expect(await screen.findByText('No completed challenges yet.')).toBeTruthy();
  expect(list).toHaveBeenCalledTimes(2);
});
