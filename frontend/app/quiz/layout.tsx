import {PlayerProvider} from '@/lib/player-context';


export default function QuizLayout({children}:{children:React.ReactNode}){
  return <PlayerProvider>{children}</PlayerProvider>;
}
