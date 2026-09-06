import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '../lib/api';
beforeEach(() => { vi.restoreAllMocks(); });
it('posts completion without a request body', async () => {
 const fetcher = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{}'));
 await api.sessions.complete(7, 'token');
 expect(fetcher).toHaveBeenCalledWith('/api/sessions/7/complete', expect.objectContaining({method:'POST'}));
});
it('interprets exhausted session response as null', async () => {
 vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null,{status:204}));
 expect(await api.sessions.next(7,'token')).toBeNull();
});
it('formats validation errors as readable text', async () => {
 vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(JSON.stringify({detail:[{msg:'Must be positive'}]}),{status:422}));
 await expect(api.sessions.start({count:0, session_type:'mixed'},'token')).rejects.toThrow('Must be positive');
});
it('refreshes an expired token and retries the authenticated request',async()=>{
 const {setRefreshHandler}=await import('../lib/api');
 const refresh=vi.fn().mockResolvedValue('fresh');setRefreshHandler(refresh);
 const f=vi.spyOn(globalThis,'fetch').mockResolvedValueOnce(new Response('{}',{status:401})).mockResolvedValueOnce(new Response('[]'));
 try {await api.domains.list('expired'); expect(refresh).toHaveBeenCalledTimes(1);expect(f).toHaveBeenLastCalledWith('/api/domains',expect.objectContaining({headers:expect.objectContaining({Authorization:'Bearer fresh'})}));}
 finally {setRefreshHandler(null);}
});
