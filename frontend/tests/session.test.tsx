import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import SessionRunner from '../components/SessionRunner';
import { api } from '../lib/api';
vi.mock('../lib/api',()=>({API_BASE:'',sessionCounts:new Map(),api:{sessions:{next:vi.fn(),answer:vi.fn(),complete:vi.fn()}}}));
const question = {id:1,question_text:'Choose a port',option_a:'First',option_b:'Second',is_multi_answer:false};
beforeEach(()=>{vi.resetAllMocks(); vi.mocked(api.sessions.next).mockResolvedValue(question as any);});
afterEach(cleanup);
it('single answer replaces previous choice and submits once',async()=>{
 vi.mocked(api.sessions.answer).mockImplementation(()=>new Promise(()=>{}));
 render(<SessionRunner sessionId={7} totalQuestions={2} mode="study"/>); await screen.findByText('First');
 fireEvent.click(screen.getByText('First'));fireEvent.click(screen.getByText('Second'));
 fireEvent.click(screen.getByText('Good'));fireEvent.click(screen.getByText('Good'));
 expect(api.sessions.answer).toHaveBeenCalledTimes(1);
 expect(api.sessions.answer).toHaveBeenCalledWith(7,expect.objectContaining({selected_options:['B']}));
});
it('shows lost session errors and a way to start again',async()=>{
 vi.mocked(api.sessions.next).mockRejectedValue(new Error('Session not found'));
 render(<SessionRunner sessionId={7} totalQuestions={2} mode="study"/>);
 expect(await screen.findByText('This session expired when the quiz service restarted.')).toBeTruthy();
 expect(screen.getByText('Start a new session')).toBeTruthy();
});
it('completes exhausted sessions and displays actual score',async()=>{
 vi.mocked(api.sessions.next).mockResolvedValue(null);
 vi.mocked(api.sessions.complete).mockResolvedValue({questions_shown:1,correct_count:1,accuracy_pct:100} as any);
 render(<SessionRunner sessionId={7} totalQuestions={1} mode="study"/>); expect(await screen.findByText('Session complete')).toBeTruthy();
 expect(api.sessions.complete).toHaveBeenCalledWith(7);
});
it('supports multiple selections and allows retry after failed submission',async()=>{
 vi.mocked(api.sessions.next).mockResolvedValue({...question,is_multi_answer:true} as any);
 vi.mocked(api.sessions.answer).mockRejectedValueOnce(new Error('Connection interrupted')).mockResolvedValue({is_correct:true,correct_option:'AB',user_selection:'AB',explanation:'Both'} as any);
 render(<SessionRunner sessionId={7} totalQuestions={2} mode="study"/>);await screen.findByText('First');fireEvent.click(screen.getByText('First'));fireEvent.click(screen.getByText('Second'));
 fireEvent.click(screen.getByText('Good'));await screen.findByText('Connection interrupted');fireEvent.click(screen.getByText('Good'));
 expect((await screen.findAllByText('Correct')).length).toBeGreaterThan(0);expect(api.sessions.answer).toHaveBeenLastCalledWith(7,expect.objectContaining({selected_options:['A','B']}));
});
