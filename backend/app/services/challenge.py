"""Question selection rules for the fixed public challenge."""

import random
from datetime import datetime

import aiosqlite


REQUIRED_QUESTIONS = {1: 3, 2: 3, 3: 3, 4: 3, 5: 3, 6: 3, 7: 2}


class ChallengePoolError(ValueError):
    def __init__(self, missing: dict[int, int]):
        self.missing = missing
        super().__init__(f"Challenge question pools are undersized: {missing}")


def select_challenge_questions(
    questions: list[dict], rng: random.Random | None = None
) -> list[dict]:
    chooser = rng or random.SystemRandom()
    pools = {
        domain: [question for question in questions if question["domain"] == domain]
        for domain in REQUIRED_QUESTIONS
    }
    missing = {
        domain: required - len(pools[domain])
        for domain, required in REQUIRED_QUESTIONS.items()
        if len(pools[domain]) < required
    }
    if missing:
        raise ChallengePoolError(missing)

    selected = [
        question
        for domain, required in REQUIRED_QUESTIONS.items()
        for question in chooser.sample(pools[domain], required)
    ]
    chooser.shuffle(selected)
    return selected


async def save_best_challenge(
    db: aiosqlite.Connection,
    *,
    user_id: int,
    correct_count: int,
    completed_at: datetime,
) -> dict:
    """Insert or improve one player's best result within the caller's transaction."""
    score = correct_count * 5
    wrong_count = 20 - correct_count
    await db.execute(
        """
        INSERT INTO challenge_records(
            user_id, score, correct_count, wrong_count, completed_at
        ) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            score = excluded.score,
            correct_count = excluded.correct_count,
            wrong_count = excluded.wrong_count,
            completed_at = excluded.completed_at
        WHERE excluded.score > challenge_records.score
        """,
        (user_id, score, correct_count, wrong_count, completed_at.isoformat()),
    )
    cursor = await db.execute(
        """
        SELECT id, score, correct_count, wrong_count, completed_at
        FROM challenge_records
        WHERE user_id = ?
        """,
        (user_id,),
    )
    record = dict(await cursor.fetchone())
    cursor = await db.execute(
        "SELECT 1 + COUNT(DISTINCT score) FROM challenge_records WHERE score > ?",
        (record["score"],),
    )
    record["rank"] = (await cursor.fetchone())[0]
    return record
