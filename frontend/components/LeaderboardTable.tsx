import {LeaderboardEntry} from '@/lib/api';

export default function LeaderboardTable({entries}:{entries:LeaderboardEntry[]}){
  return <div className="table-scroll">
    <table className="leaderboard-table">
      <thead><tr><th>Rank</th><th>Name</th><th>Score</th><th>Correct</th><th>Wrong</th></tr></thead>
      <tbody>{entries.map((entry,index)=><tr key={`${entry.rank}-${entry.name}-${index}`}>
        <td>{entry.rank}</td><th scope="row">{entry.name}</th><td>{entry.score}</td><td>{entry.correct}</td><td>{entry.wrong}</td>
      </tr>)}</tbody>
    </table>
  </div>;
}
