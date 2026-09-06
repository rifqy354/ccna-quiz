import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '../lib/api';
beforeEach(() => { vi.restoreAllMocks(); });
it('posts completion without a request body', async () => {
 const fetcher = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{}'));
 await api.sessions.complete(7);
 expect(fetcher).toHaveBeenCalledWith('/api/sessions/7/complete', expect.objectContaining({method:'POST',credentials:'same-origin'}));
});
it('interprets exhausted session response as null', async () => {
 vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null,{status:204}));
 expect(await api.sessions.next(7)).toBeNull();
});
it('formats validation errors as readable text', async () => {
 vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(JSON.stringify({detail:[{msg:'Must be positive'}]}),{status:422}));
 await expect(api.sessions.start({count:0, session_type:'mixed'})).rejects.toThrow('Must be positive');
});

it('uses same-origin cookies for player identity without authorization', async () => {
 const fetcher = vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(JSON.stringify({name:'Rifqy'})));
 expect(await api.player.me()).toEqual({name:'Rifqy'});
 expect(fetcher).toHaveBeenCalledWith('/api/player/me',{
  method:'GET',credentials:'same-origin',headers:{'Content-Type':'application/json'},
 });
});

it('creates a challenge without a client-controlled request body', async () => {
 const fetcher = vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(JSON.stringify({session_id:7,total_questions:20,session_type:'challenge'})));
 expect((await api.sessions.challenge()).total_questions).toBe(20);
 expect(fetcher).toHaveBeenCalledWith('/api/sessions/challenge',{
  method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},
 });
});

it('reads the public leaderboard with the approved fields', async () => {
 vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(JSON.stringify([
  {rank:1,name:'Rifqy',score:90,correct:18,wrong:2},
 ])));
 expect(await api.leaderboard.list()).toEqual([
  {rank:1,name:'Rifqy',score:90,correct:18,wrong:2},
 ]);
});
