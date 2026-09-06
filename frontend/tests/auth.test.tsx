import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, afterEach, expect, it, vi } from 'vitest';
import { AuthProvider,useAuth } from '../lib/auth-context';
vi.mock('next/navigation',()=>({usePathname:()=>'/register',useRouter:()=>({replace:vi.fn()})}));
function Consumer(){const a=useAuth();return <><p>{a.loading?'Loading':a.user?.name || 'Guest'}</p><button onClick={a.logout}>Logout</button><button onClick={()=>a.register('a@b.com','password','Name').catch(e=>document.title=e.message)}>Register</button></>;}
beforeEach(()=>{localStorage.clear();vi.restoreAllMocks();document.title='';});afterEach(cleanup);
it('surfaces registration failure without attempting login',async()=>{
 const f=vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(JSON.stringify({detail:'Email already registered'}),{status:400}));
 render(<AuthProvider><Consumer/></AuthProvider>);fireEvent.click(screen.getByText('Register'));
 await waitFor(()=>expect(document.title).toBe('Email already registered'));expect(f).toHaveBeenCalledTimes(1);
});
it('keeps auth loading until identity verification and ignores corrupt cache',async()=>{
 localStorage.setItem('access_token','saved');localStorage.setItem('user','{bad');
 let resolve!: (r:Response)=>void;vi.spyOn(globalThis,'fetch').mockImplementation(()=>new Promise(r=>resolve=r));
 render(<AuthProvider><Consumer/></AuthProvider>);expect(screen.getByText('Loading')).toBeTruthy();
 resolve(new Response(JSON.stringify({id:1,name:'Verified',email:'a@b.com'})));
 expect(await screen.findByText('Verified')).toBeTruthy();
});

it('does not restore identity when verification finishes after logout',async()=>{
 localStorage.setItem('access_token','saved');
 let resolve!: (r:Response)=>void;vi.spyOn(globalThis,'fetch').mockImplementation(()=>new Promise(r=>resolve=r));
 render(<AuthProvider><Consumer/></AuthProvider>);fireEvent.click(screen.getByText('Logout'));
 resolve(new Response(JSON.stringify({id:1,name:'Verified',email:'a@b.com'})));
 await waitFor(()=>expect(screen.getByText('Guest')).toBeTruthy());
 expect(localStorage.getItem('user')).toBeNull();
});
