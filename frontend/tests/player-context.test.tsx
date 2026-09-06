import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';

const mocks=vi.hoisted(()=>({me:vi.fn(),create:vi.fn()}));
vi.mock('../lib/api',()=>{
 class ApiError extends Error { constructor(public status:number,message:string){super(message);} }
 return {ApiError,api:{player:{me:mocks.me,create:mocks.create}}};
});

import {ApiError} from '../lib/api';
import {PlayerProvider,usePlayer} from '../lib/player-context';

function Consumer(){
 const state=usePlayer();
 return <>
  <p>{state.loading?'Loading':state.player?.name||'Guest'}</p>
  {state.error&&<p role="alert">{state.error}</p>}
  <button onClick={()=>state.createPlayer('Rifqy')}>Create</button>
  <button onClick={state.refreshPlayer}>Retry</button>
  <button onClick={state.clearPlayer}>Clear</button>
 </>;
}

beforeEach(()=>{mocks.me.mockReset();mocks.create.mockReset();});
afterEach(cleanup);

it('keeps loading until a returning player is verified',async()=>{
 let resolve!:(value:{name:string})=>void;
 mocks.me.mockImplementation(()=>new Promise(r=>{resolve=r;}));
 render(<PlayerProvider><Consumer/></PlayerProvider>);
 expect(screen.getByText('Loading')).toBeTruthy();
 resolve({name:'Returning Player'});
 expect(await screen.findByText('Returning Player')).toBeTruthy();
});

it('treats a 401 as a first visit',async()=>{
 mocks.me.mockRejectedValue(new ApiError(401,'Player identity required'));
 render(<PlayerProvider><Consumer/></PlayerProvider>);
 expect(await screen.findByText('Guest')).toBeTruthy();
 expect(screen.queryByRole('alert')).toBeNull();
});

it('creates a player and never reads or writes browser storage',async()=>{
 const getItem=vi.spyOn(Storage.prototype,'getItem');
 const setItem=vi.spyOn(Storage.prototype,'setItem');
 mocks.me.mockRejectedValue(new ApiError(401,'Player identity required'));
 mocks.create.mockResolvedValue({name:'Rifqy'});
 render(<PlayerProvider><Consumer/></PlayerProvider>);
 await screen.findByText('Guest');
 fireEvent.click(screen.getByText('Create'));
 expect(await screen.findByText('Rifqy')).toBeTruthy();
 expect(mocks.create).toHaveBeenCalledWith('Rifqy');
 expect(getItem).not.toHaveBeenCalled();
 expect(setItem).not.toHaveBeenCalled();
});

it('surfaces player creation errors without inventing identity',async()=>{
 mocks.me.mockRejectedValue(new ApiError(401,'Player identity required'));
 mocks.create.mockRejectedValue(new Error('Name must contain 2–24 visible characters'));
 render(<PlayerProvider><Consumer/></PlayerProvider>);
 await screen.findByText('Guest');
 fireEvent.click(screen.getByText('Create'));
 expect((await screen.findByRole('alert')).textContent).toBe('Name must contain 2–24 visible characters');
 expect(screen.getByText('Guest')).toBeTruthy();
});

it('clears identity and can retry a failed lookup',async()=>{
 mocks.me.mockResolvedValueOnce({name:'Rifqy'}).mockResolvedValueOnce({name:'Recovered'});
 render(<PlayerProvider><Consumer/></PlayerProvider>);
 await screen.findByText('Rifqy');
 fireEvent.click(screen.getByText('Clear'));
 expect(screen.getByText('Guest')).toBeTruthy();
 fireEvent.click(screen.getByText('Retry'));
 await waitFor(()=>expect(screen.getByText('Recovered')).toBeTruthy());
});
