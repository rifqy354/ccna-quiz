"""Graded correctness must govern persisted mastery and review scheduling."""
import asyncio
from datetime import date, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app import database
from app.guest import get_current_player
from app.main import app
from app.routers import sessions


@pytest_asyncio.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "_resolve_db_path", lambda: str(tmp_path / "quiz.db"))
    monkeypatch.setattr(sessions, "_session_cache", {})
    await database.init_db()
    async with database.get_db() as db:
        await db.execute("INSERT INTO users(id,email,password_hash,name) VALUES(1,'learner@example.test','unused','Learner')")
        await db.execute(
            "INSERT INTO questions(id,source_book,source_chapter,book_title,domain,question_text,"
            "option_a,option_b,option_c,option_d,option_e,option_f,correct_option,explanation) "
            "VALUES(101,'test','ch1','Book',1,'Choose two','a','b','c','d','e','f','DF','Explanation')"
        )
        await db.commit()

    async def current_user():
        return {"id": 1}

    monkeypatch.setattr(app, "dependency_overrides", {get_current_player: current_user})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as ac:
        yield ac


async def seed_progress(streak):
    async with database.get_db() as db:
        await db.execute(
            "INSERT INTO user_progress(user_id,question_id,attempts,correct_count,consecutive_correct,"
            "ease_factor,interval_days,next_review_date,mastered,mastered_at) "
            "VALUES(1,101,?,?,?,?,20,'2000-01-01',?,?)",
            (streak, streak, streak, 2.5, int(streak >= 5), '2000-01-01' if streak >= 5 else None),
        )
        await db.commit()


async def start(client, returning=True):
    response = await client.post("/api/sessions/start", json={
        "count": 1, "session_type": "review" if returning else "new",
    })
    assert response.status_code == 200
    assert response.json()["total_questions"] == 1
    return response.json()["session_id"]


async def submit(client, sid, selected, confidence):
    response = await client.post(f"/api/sessions/{sid}/answer", json={
        "question_id": 101, "selected_options": selected, "confidence": confidence,
    })
    assert response.status_code == 200
    return response.json()


async def progress():
    async with database.get_db() as db:
        cursor = await db.execute("SELECT * FROM user_progress WHERE user_id=1 AND question_id=101")
        return dict(await cursor.fetchone())


@pytest.mark.asyncio
@pytest.mark.parametrize("confidence", ["again", "hard", "good", "easy"])
@pytest.mark.parametrize("streak", [None, 4, 5])
async def test_wrong_answer_resets_progress_regardless_of_confidence(client, confidence, streak):
    if streak is not None:
        await seed_progress(streak)
    sid = await start(client, returning=streak is not None)
    result = await submit(client, sid, ["D"], confidence)  # Partial multi-answer is wrong.
    assert result["is_correct"] is False
    assert result["mastered"] is False
    assert result["next_review_days"] == 1
    saved = await progress()
    assert saved["attempts"] == (streak or 0) + 1
    assert saved["correct_count"] == (streak or 0)
    assert saved["consecutive_correct"] == 0
    assert saved["mastered"] == 0
    assert saved["mastered_at"] is None
    assert saved["interval_days"] == 1
    assert saved["ease_factor"] == pytest.approx(2.3)
    assert saved["next_review_date"] == (date.today() + timedelta(days=1)).isoformat()
    async with database.get_db() as db:
        cursor = await db.execute("SELECT selected_option, is_correct, confidence FROM user_responses")
        assert tuple(await cursor.fetchone()) == ("D", 0, confidence)
    domains = (await client.get("/api/domains")).json()
    assert next(d for d in domains if d["domain"] == 1)["mastered"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("confidence, interval", [("hard", 40), ("good", 50), ("easy", 65)])
async def test_correct_answer_still_earns_mastery(client, confidence, interval):
    await seed_progress(4)
    result = await submit(client, await start(client), ["F", "D"], confidence)
    assert result["is_correct"] is True
    assert result["mastered"] is True
    assert result["next_review_days"] == interval
    saved = await progress()
    assert saved["consecutive_correct"] == 5
    assert saved["mastered_at"] == date.today().isoformat()


@pytest.mark.asyncio
async def test_correct_again_can_reset_mastery_without_losing_correct_count(client):
    await seed_progress(5)
    result = await submit(client, await start(client), ["D", "F"], "again")
    assert result["is_correct"] is True
    assert result["mastered"] is False
    saved = await progress()
    assert saved["correct_count"] == 6
    assert saved["consecutive_correct"] == 0
    assert saved["mastered_at"] is None


@pytest.mark.asyncio
async def test_open_session_cannot_restore_streak_from_before_wrong_answer(client):
    await seed_progress(4)
    first, second = await start(client), await start(client)
    await submit(client, first, ["D"], "again")
    result = await submit(client, second, ["D", "F"], "good")
    assert result["mastered"] is False
    saved = await progress()
    assert saved["consecutive_correct"] == 1
    assert saved["attempts"] == 6
    assert saved["correct_count"] == 5
    assert saved["interval_days"] == 2
    assert saved["ease_factor"] == pytest.approx(2.3)


@pytest.mark.asyncio
async def test_continuing_mastery_keeps_original_date(client):
    await seed_progress(5)
    await submit(client, await start(client), ["D", "F"], "good")
    assert (await progress())["mastered_at"] == "2000-01-01"


@pytest.mark.asyncio
async def test_concurrent_sessions_do_not_lose_learning_updates(client):
    await seed_progress(4)
    first, second = await start(client), await start(client)
    await asyncio.gather(
        submit(client, first, ["D", "F"], "good"),
        submit(client, second, ["D", "F"], "good"),
    )
    saved = await progress()
    assert saved["attempts"] == 6
    assert saved["correct_count"] == 6
    assert saved["consecutive_correct"] == 6
    assert saved["interval_days"] == 125  # 20 → 50 → 125, rather than two stale updates to 50.
