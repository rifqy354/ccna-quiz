"""Returning learners must retain question identity when progress is merged."""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app import database
from app.auth import get_current_user
from app.main import app
from app.routers import sessions


@pytest_asyncio.fixture
async def returning_learner(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "_resolve_db_path", lambda: str(tmp_path / "quiz.db"))
    monkeypatch.setattr(sessions, "_session_cache", {})
    await database.init_db()
    async with database.get_db() as db:
        await db.executemany(
            "INSERT INTO users(id, email, password_hash, name) VALUES (?, ?, 'unused', 'Learner')",
            [(1, "one@example.test"), (2, "two@example.test")],
        )
        await db.executemany(
            "INSERT INTO questions(id, source_book, source_chapter, book_title, domain, "
            "question_text, option_a, option_b, option_c, option_d, option_e, option_f, "
            "correct_option, explanation) VALUES (?, 'test', 'ch1', 'Book', 1, ?, "
            "'A text', 'B text', 'C text', 'D text', 'E text', 'F text', ?, 'Explanation')",
            [(101, "Returning question?", "DF"), (7, "New question?", "A")],
        )
        await db.execute(
            "INSERT INTO user_progress(id, user_id, question_id, attempts, correct_count, "
            "consecutive_correct, ease_factor, interval_days, next_review_date) "
            "VALUES (7, 1, 101, 2, 2, 2, 2.0, 4, '2000-01-01')"
        )
        # This other learner's progress must not make question 7 a review for user 1.
        await db.execute(
            "INSERT INTO user_progress(id, user_id, question_id, attempts, mastered, next_review_date) "
            "VALUES (8, 2, 7, 5, 1, '2000-01-01')"
        )
        await db.commit()

    async def current_user():
        return {"id": 1}

    monkeypatch.setattr(app, "dependency_overrides", {get_current_user: current_user})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
@pytest.mark.parametrize("session_type", ["review", "mixed"])
@pytest.mark.parametrize("progress_id", [7, 700])
async def test_returning_answer_keeps_question_id_and_updates_its_progress(
    returning_learner, session_type, progress_id,
):
    client = returning_learner
    async with database.get_db() as db:
        await db.execute("UPDATE user_progress SET id = ? WHERE user_id = 1", (progress_id,))
        await db.commit()
    started = await client.post("/api/sessions/start", json={"session_type": session_type, "count": 2})
    assert started.status_code == 200
    assert started.json()["total_questions"] == (1 if session_type == "review" else 2)
    sid = started.json()["session_id"]
    question = await client.get(f"/api/sessions/{sid}/next")
    assert question.status_code == 200
    assert question.json()["id"] == 101
    assert question.json()["question_text"] == "Returning question?"
    assert question.json()["is_multi_answer"] is True

    answer = await client.post(f"/api/sessions/{sid}/answer", json={
        "question_id": 101, "selected_options": ["F", "D"], "confidence": "good",
    })
    assert answer.status_code == 200
    assert answer.json()["is_correct"] is True
    assert answer.json()["next_review_days"] == 8  # Existing interval 4 × ease 2.0.
    async with database.get_db() as db:
        cursor = await db.execute(
            "SELECT id, question_id, attempts, correct_count, consecutive_correct, interval_days "
            "FROM user_progress WHERE user_id = 1"
        )
        assert [tuple(row) for row in await cursor.fetchall()] == [(progress_id, 101, 3, 3, 3, 8)]
        cursor = await db.execute("SELECT question_id, selected_option, is_correct FROM user_responses")
        assert [tuple(row) for row in await cursor.fetchall()] == [(101, "DF", 1)]
        cursor = await db.execute("SELECT attempts, mastered FROM user_progress WHERE user_id = 2")
        assert tuple(await cursor.fetchone()) == (5, 1)
    if session_type == "mixed":
        next_question = await client.get(f"/api/sessions/{sid}/next")
        assert next_question.json()["id"] == 7
        assert next_question.json()["question_text"] == "New question?"


@pytest.mark.asyncio
async def test_new_mode_excludes_own_progress_but_not_other_learners_progress(returning_learner):
    started = await returning_learner.post("/api/sessions/start", json={"session_type": "new", "count": 2})
    assert started.status_code == 200
    assert started.json()["total_questions"] == 1
    sid = started.json()["session_id"]
    question = await returning_learner.get(f"/api/sessions/{sid}/next")
    assert question.json()["id"] == 7
