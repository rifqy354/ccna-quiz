"""Answer retries and concurrent requests must not duplicate learning history."""
import asyncio
import sqlite3

import aiosqlite
import pytest
import pytest_asyncio
from fastapi import Header
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
        await db.execute("INSERT INTO users(id,email,password_hash,name) VALUES(1,'test@example.test','unused','Test')")
        await db.executemany(
            "INSERT INTO questions(id,source_book,source_chapter,book_title,domain,question_text,"
            "option_a,option_b,option_c,option_d,correct_option,explanation) "
            "VALUES(?,'test','ch1','Book',1,'Question?','a','b','c','d','A','Explanation')",
            [(101,), (102,)],
        )
        await db.commit()

    async def current_user(x_user_id: int = Header(default=1)):
        return {"id": x_user_id}

    monkeypatch.setattr(app, "dependency_overrides", {get_current_player: current_user})
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="https://test") as ac:
        yield ac


async def start(client, count=1, session_type="new"):
    response = await client.post("/api/sessions/start", json={"count": count, "session_type": session_type})
    assert response.status_code == 200
    sid = response.json()["session_id"]
    question = await client.get(f"/api/sessions/{sid}/next")
    assert question.status_code in (200, 204)
    return sid, question.json().get("id") if question.status_code == 200 else None


def answer(qid):
    return {"question_id": qid, "selected_options": ["A"], "confidence": "good"}


async def history_counts():
    async with database.get_db() as db:
        cursor = await db.execute("SELECT COUNT(*) FROM user_responses")
        responses = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COALESCE(SUM(attempts), 0), COALESCE(SUM(correct_count), 0) FROM user_progress")
        return responses, tuple(await cursor.fetchone())


@pytest.mark.asyncio
@pytest.mark.parametrize("count", [1, 2])
@pytest.mark.parametrize("returning", [False, True])
async def test_concurrent_duplicate_answer_is_recorded_once(client, count, returning):
    if returning:
        async with database.get_db() as db:
            await db.execute("INSERT INTO user_progress(user_id,question_id,attempts,correct_count,next_review_date) "
                             "VALUES(1,101,2,2,'2000-01-01')")
            await db.commit()
    sid, qid = await start(client, count, "review" if returning else "new")
    responses = await asyncio.gather(*[
        client.post(f"/api/sessions/{sid}/answer", json=answer(qid)) for _ in range(2)
    ])
    assert sorted(r.status_code for r in responses) == [200, 409]
    expected_attempts = 3 if returning else 1
    assert await history_counts() == (1, (expected_attempts, expected_attempts))
    if count == 2 and not returning:
        next_question = await client.get(f"/api/sessions/{sid}/next")
        assert next_question.json()["id"] != qid
    summary = await client.post(f"/api/sessions/{sid}/complete")
    assert summary.status_code == 200
    assert summary.json()["correct_count"] == 1


@pytest.mark.asyncio
async def test_submission_after_final_answer_returns_conflict(client):
    sid, qid = await start(client)
    assert (await client.post(f"/api/sessions/{sid}/answer", json=answer(qid))).status_code == 200
    assert (await client.post(f"/api/sessions/{sid}/answer", json=answer(qid))).status_code == 409
    assert await history_counts() == (1, (1, 1))


@pytest.mark.asyncio
async def test_empty_review_session_rejects_answer_without_writes(client):
    sid, _ = await start(client, session_type="review")
    response = await client.post(f"/api/sessions/{sid}/answer", json=answer(101))
    assert response.status_code == 409
    assert await history_counts() == (0, (0, 0))


@pytest.mark.asyncio
async def test_failed_commit_can_be_retried_without_inflating_score(client, monkeypatch):
    sid, qid = await start(client)
    original_commit = aiosqlite.Connection.commit
    fail_once = True

    async def commit(db):
        nonlocal fail_once
        if fail_once:
            fail_once = False
            raise sqlite3.OperationalError("Simulated commit failure")
        await original_commit(db)

    monkeypatch.setattr(aiosqlite.Connection, "commit", commit)
    assert (await client.post(f"/api/sessions/{sid}/answer", json=answer(qid))).status_code == 500
    assert await history_counts() == (0, (0, 0))
    assert (await client.post(f"/api/sessions/{sid}/answer", json=answer(qid))).status_code == 200
    summary = await client.post(f"/api/sessions/{sid}/complete")
    assert summary.json()["correct_count"] == 1
    assert await history_counts() == (1, (1, 1))


@pytest.mark.asyncio
async def test_concurrent_completion_is_safe(client):
    sid, _ = await start(client)
    responses = await asyncio.gather(*[client.post(f"/api/sessions/{sid}/complete") for _ in range(2)])
    assert sorted(r.status_code for r in responses) == [200, 404]


@pytest.mark.asyncio
@pytest.mark.parametrize("first", ["answer", "complete"])
async def test_answer_and_completion_share_the_same_session_lock(client, monkeypatch, first):
    sid, qid = await start(client)
    committing = asyncio.Event()
    release_commit = asyncio.Event()
    second_started = asyncio.Event()
    original_commit = aiosqlite.Connection.commit
    pause_once = True

    async def commit(db):
        nonlocal pause_once
        if pause_once:
            pause_once = False
            committing.set()
            await release_commit.wait()
        await original_commit(db)

    second = "complete" if first == "answer" else "answer"

    async def request_started(request):
        if request.url.path.endswith("/" + second):
            second_started.set()

    monkeypatch.setattr(aiosqlite.Connection, "commit", commit)
    client.event_hooks["request"].append(request_started)

    async def submit(operation):
        return await client.post(f"/api/sessions/{sid}/{operation}",
                                 json=answer(qid) if operation == "answer" else None)

    tasks = [asyncio.create_task(submit(first))]
    try:
        await asyncio.wait_for(committing.wait(), 3)
        tasks.append(asyncio.create_task(submit(second)))
        await asyncio.wait_for(second_started.wait(), 3)
    finally:
        release_commit.set()
        results = await asyncio.wait_for(asyncio.gather(*tasks), 3)
    assert results[0].status_code == 200
    assert results[1].status_code == (200 if first == "answer" else 404)
    summary = results[1] if first == "answer" else results[0]
    assert summary.json()["correct_count"] == (1 if first == "answer" else 0)
    assert await history_counts() == ((1, (1, 1)) if first == "answer" else (0, (0, 0)))


@pytest.mark.asyncio
async def test_rejected_request_does_not_consume_question(client):
    sid, qid = await start(client)
    url = f"/api/sessions/{sid}/answer"
    assert (await client.post(url, json=answer(qid), headers={"x-user-id": "2"})).status_code == 404
    assert (await client.post(url, json=answer(999))).status_code == 409
    assert (await client.post(url, json={**answer(qid), "selected_options": ["Z"]})).status_code == 422
    assert await history_counts() == (0, (0, 0))
    assert (await client.post(url, json=answer(qid))).status_code == 200
