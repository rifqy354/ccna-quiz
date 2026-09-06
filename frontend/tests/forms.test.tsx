import {cleanup,fireEvent,render,screen} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';

const createPlayer=vi.hoisted(()=>vi.fn(()=>new Promise<void>(()=>{})));
vi.mock('../lib/player-context',()=>({usePlayer:()=>({createPlayer,error:null})}));

import NamePrompt from '../components/NamePrompt';

afterEach(()=>{cleanup();createPlayer.mockClear();});

it('labels the name field and blocks repeated submissions while pending',()=>{
  render(<NamePrompt/>);
  fireEvent.change(screen.getByLabelText('Your name'),{target:{value:'Rifqy'}});
  const button=screen.getByRole('button',{name:'Enter the quiz'});
  fireEvent.click(button);fireEvent.click(button);
  expect(createPlayer).toHaveBeenCalledTimes(1);
  expect(createPlayer).toHaveBeenCalledWith('Rifqy');
  expect((button as HTMLButtonElement).disabled).toBe(true);
});
