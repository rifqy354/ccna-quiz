from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.main import app
from app.services.challenge import save_best_challenge


pytestmark = pytest.mark.asyncio


async def _seed_record(
    *, user_id: int, public_id: str, name: str, score: int, completed_at: datetime
):
    correct = score // 5
    async with get_db() as db:
        await db.execute(
            "INSERT INTO users(id,email,password_hash,name) VALUES(?,?,?,?)",
            (user_id, f"guest-{public_id}@internal.invalid", "!", name),
        )
        await db.execute(
            "INSERT INTO guest_players(user_id,public_id,display_name) VALUES(?,?,?)",
            (user_id, public_id, name),
        )
        await db.execute(
            """
            INSERT INTO challenge_records(
                user_id,score,correct_count,wrong_count,completed_at
            ) VALUES(?,?,?,?,?)
            """,
            (user_id, score, correct, 20 - correct, completed_at.isoformat()),
        )
        await db.commit()


async def test_public_leaderboard_has_dense_ranks_and_only_approved_fields():
    start = datetime(2026, 9, 6, tzinfo=timezone.utc)
    rows = [
        (101, "1" * 32, "Ace", 100, start),
        (102, "2" * 32, "Same Name", 90, start + timedelta(minutes=2)),
        (103, "3" * 32, "Same Name", 90, start + timedelta(minutes=1)),
        (104, "4" * 32, "Rookie", 75, start),
    ]
    for user_id, public_id, name, score, completed_at in rows:
        await _seed_record(
            user_id=user_id,
            public_id=public_id,
            name=name,
            score=score,
            completed_at=completed_at,
        )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://test"
    ) as client:
        response = await client.get("/api/leaderboard")

    assert response.status_code == 200
    leaderboard = response.json()
    assert [row["rank"] for row in leaderboard] == [1, 2, 2, 3]
    assert [row["name"] for row in leaderboard] == [
        "Ace", "Same Name", "Same Name", "Rookie",
    ]
    assert [row["score"] for row in leaderboard] == [100, 90, 90, 75]
    assert [row["correct"] for row in leaderboard] == [20, 18, 18, 15]
    assert [row["wrong"] for row in leaderboard] == [0, 2, 2, 5]
    assert all(
        set(row) == {"rank", "name", "score", "correct", "wrong"}
        for row in leaderboard
    )


async def test_leaderboard_is_available_without_player_cookie():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://test"
    ) as client:
        response = await client.get("/api/leaderboard")
    assert response.status_code == 200


async def test_best_result_changes_only_for_a_strictly_higher_score():
    start = datetime(2026, 9, 6, tzinfo=timezone.utc)
    async with get_db() as db:
        await db.execute(
            "INSERT INTO users(id,email,password_hash,name) "
            "VALUES(201,'guest-best@internal.invalid','!','Best')"
        )
        await db.execute(
            "INSERT INTO guest_players(user_id,public_id,display_name) "
            "VALUES(201,?,'Best')",
            ("b" * 32,),
        )
        first = await save_best_challenge(
            db, user_id=201, correct_count=10, completed_at=start
        )
        await db.commit()
        assert (first["score"], first["correct_count"], first["wrong_count"]) == (50, 10, 10)

        lower = await save_best_challenge(
            db, user_id=201, correct_count=8, completed_at=start + timedelta(hours=1)
        )
        equal = await save_best_challenge(
            db, user_id=201, correct_count=10, completed_at=start + timedelta(hours=2)
        )
        await db.commit()
        assert lower["completed_at"] == start.isoformat()
        assert equal["completed_at"] == start.isoformat()

        higher_time = start + timedelta(hours=3)
        higher = await save_best_challenge(
            db, user_id=201, correct_count=12, completed_at=higher_time
        )
        await db.commit()
        assert (higher["score"], higher["correct_count"], higher["wrong_count"]) == (60, 12, 8)
        assert higher["completed_at"] == higher_time.isoformat()
