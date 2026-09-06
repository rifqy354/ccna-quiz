import {cleanup,render,screen} from '@testing-library/react';
import {afterEach,expect,it} from 'vitest';

import PortfolioPage from '../app/portfolio/page';
import WriteupsPage from '../app/portfolio/writeups/page';


afterEach(cleanup);


it('presents Rifqy and the two primary work areas',()=>{
  render(<PortfolioPage/>);
  expect(screen.getByRole('heading',{name:'Rifqy'})).toBeTruthy();
  expect(screen.getByText('Networking and security student')).toBeTruthy();
  expect(screen.getAllByRole('link',{name:/CTF Writeups/i})[0].getAttribute('href')).toBe('/writeups');
  expect(screen.getAllByRole('link',{name:/CCNA Quiz/i})[0].getAttribute('href')).toBe('https://quiz.email2.my.id/');
  expect(screen.getByRole('navigation',{name:'Primary'})).toBeTruthy();
});


it('shows an honest empty writeup index',()=>{
  render(<WriteupsPage/>);
  expect(screen.getByRole('heading',{name:'CTF Writeups'})).toBeTruthy();
  expect(screen.getByText('0 published')).toBeTruthy();
  expect(screen.getByText(/writeups will appear here/i)).toBeTruthy();
  expect(screen.getByRole('link',{name:/Back to portfolio/i}).getAttribute('href')).toBe('/');
});
