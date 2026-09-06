import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import Login from '../app/login/page';
const {login}=vi.hoisted(()=>({login:vi.fn(()=>new Promise(()=>{}))}));
vi.mock('../lib/auth-context',()=>({useAuth:()=>({login})}));
vi.mock('next/navigation',()=>({useRouter:()=>({push:vi.fn()})}));
afterEach(cleanup);
it('disables repeated login submissions while pending',()=>{
 render(<Login/>);fireEvent.change(screen.getByLabelText('Email'),{target:{value:'a@b.com'}});fireEvent.change(screen.getByLabelText('Password'),{target:{value:'password'}});
 const button=screen.getByRole('button',{name:'Login'});fireEvent.click(button);fireEvent.click(button);expect(login).toHaveBeenCalledTimes(1);expect((button as HTMLButtonElement).disabled).toBe(true);
});
