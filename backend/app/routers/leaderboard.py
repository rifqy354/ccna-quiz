"""Public best-score leaderboard."""

from fastapi import APIRouter

from ..database import get_db
from ..models import LeaderboardEntry


router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])


@router.get("", response_model=list[LeaderboardEntry])
async def leaderboard():
    async with get_db() as db:
        cursor = await db.execute(
            """
            WITH ranked AS (
                SELECT
                    c.id,
                    DENSE_RANK() OVER (ORDER BY c.score DESC) AS rank,
                    g.display_name AS name,
                    c.score,
                    c.correct_count AS correct,
                    c.wrong_count AS wrong,
                    c.completed_at
                FROM challenge_records c
                JOIN guest_players g ON g.user_id = c.user_id
            )
            SELECT rank, name, score, correct, wrong
            FROM ranked
            ORDER BY rank ASC, completed_at ASC, id ASC
            """
        )
        return [LeaderboardEntry(**dict(row)) for row in await cursor.fetchall()]
