import pytest_asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db, get_db

pytest_plugins = ['pytest_asyncio']


@pytest_asyncio.fixture
async def client():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def player(client):
    response = await client.post("/api/player", json={"name": "Session Player"})
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_start_session_requires_auth(client):
    resp = await client.post("/api/sessions/start", json={"count": 5})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_start_session_empty_db(client, player):
    resp = await client.post("/api/sessions/start", json={"domain": 1, "count": 5})
    # 404 when no questions in DB is expected
    assert resp.status_code in (200, 404)


@pytest.mark.asyncio
async def test_dashboard_requires_auth(client):
    resp = await client.get("/api/stats/dashboard")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_dashboard_returns_stats(client, player):
    resp = await client.get("/api/stats/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_questions" in data
    assert "study_streak" in data
    assert "domains" in data
    assert len(data["domains"]) == 7


@pytest.mark.asyncio
async def test_weak_areas_requires_auth(client):
    resp = await client.get("/api/stats/weak-areas")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_weak_areas_returns_empty_list(client, player):
    resp = await client.get("/api/stats/weak-areas")
    assert resp.status_code == 200
    data = resp.json()
    assert "weak_areas" in data


@pytest.mark.asyncio
async def test_players_cannot_access_each_others_sessions():
    transport = ASGITransport(app=app)
    async with (
        AsyncClient(transport=transport, base_url="https://test") as first,
        AsyncClient(transport=transport, base_url="https://test") as second,
    ):
        assert (await first.post("/api/player", json={"name": "First Player"})).status_code == 201
        assert (await second.post("/api/player", json={"name": "Second Player"})).status_code == 201
        started = await first.post("/api/sessions/start", json={"count": 1})
        assert started.status_code == 200
        session_id = started.json()["session_id"]
        question = await first.get(f"/api/sessions/{session_id}/next")
        assert question.status_code == 200

        assert (await second.get(f"/api/sessions/{session_id}/next")).status_code == 404
        forbidden_answer = await second.post(
            f"/api/sessions/{session_id}/answer",
            json={
                "question_id": question.json()["id"],
                "selected_options": ["A"],
                "confidence": "good",
            },
        )
        assert forbidden_answer.status_code == 404




# ── Multi-answer integration tests ──────────────────────────────────────────

async def _find_multi_question(client, count=50):
    """Start a session and return the first multi-answer question found.

    Each get_next() call must be paired with an answer() call to advance
    the session cache index.
    """
    r = await client.post("/api/sessions/start",
        json={"session_type": "mixed", "count": count})
    if r.status_code != 200:
        return None
    sid = r.json()["session_id"]
    for _ in range(count):
        r = await client.get(f"/api/sessions/{sid}/next")
        if r.status_code != 200:
            break
        q = r.json()
        # is_multi_answer is the authoritative flag from the backend
        if q.get("is_multi_answer"):
            # QuestionResponse omits correct_option (security); fetch it from DB
            async with get_db() as db:
                cursor = await db.execute(
                    "SELECT correct_option FROM questions WHERE id = ?", (q["id"],)
                )
                row = await cursor.fetchone()
                q["correct_option"] = dict(row)["correct_option"] if row else ""
            return sid, q
        # Advance index by submitting a dummy answer
        r = await client.post(f"/api/sessions/{sid}/answer",
            json={"question_id": q["id"], "selected_options": ["A"],
                  "confidence": "good", "response_time_ms": 100},
        )
    return None


@pytest.mark.asyncio
async def test_answer_multi_correct(client, player):
    """Full multi-answer selection is graded correct."""
    result = await _find_multi_question(client)
    if result is None:
        pytest.skip("No multi-answer question in first 100 session questions")
    sid, q = result
    correct = q["correct_option"]
    r = await client.post(f"/api/sessions/{sid}/answer",
        json={"question_id": q["id"], "selected_options": list(correct),
              "confidence": "good", "response_time_ms": 1000},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["is_correct"] is True
    assert data["user_selection"] == correct


@pytest.mark.asyncio
async def test_answer_multi_partial_is_wrong(client, player):
    """Partial multi-answer (subset) is graded incorrect."""
    result = await _find_multi_question(client)
    if result is None:
        pytest.skip("No multi-answer question in first 100 session questions")
    sid, q = result
    correct = q["correct_option"]
    partial = [list(correct)[0]]
    r = await client.post(f"/api/sessions/{sid}/answer",
        json={"question_id": q["id"], "selected_options": partial,
              "confidence": "good", "response_time_ms": 1000},
    )
    assert r.status_code == 200
    assert r.json()["is_correct"] is False


@pytest.mark.asyncio
async def test_answer_multi_reversed_order_is_correct(client, player):
    """Multi-answer selection order does not affect correctness."""
    result = await _find_multi_question(client)
    if result is None:
        pytest.skip("No multi-answer question in first 100 session questions")
    sid, q = result
    correct = q["correct_option"]
    r = await client.post(f"/api/sessions/{sid}/answer",
        json={"question_id": q["id"], "selected_options": list(correct)[::-1],
              "confidence": "good", "response_time_ms": 1000},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["is_correct"] is True
    assert data["user_selection"] == correct


@pytest.mark.asyncio
async def test_answer_multi_superset_is_wrong(client, player):
    """Multi-answer superset (extra letters) is graded incorrect."""
    result = await _find_multi_question(client)
    if result is None:
        pytest.skip("No multi-answer question in first 100 session questions")
    sid, q = result
    correct = q["correct_option"]
    letters = list(correct)
    extra = "A" if "A" not in letters else "B"
    r = await client.post(f"/api/sessions/{sid}/answer",
        json={"question_id": q["id"], "selected_options": letters + [extra],
              "confidence": "good", "response_time_ms": 1000},
    )
    assert r.status_code == 200
    assert r.json()["is_correct"] is False


@pytest.mark.asyncio
async def test_answer_duplicate_submission_rejected(client, player):
    """Submitting the same question twice returns 409 Conflict."""
    r = await client.post("/api/sessions/start",
        json={"session_type": "mixed", "count": 5})
    assert r.status_code == 200
    sid = r.json()["session_id"]
    r = await client.get(f"/api/sessions/{sid}/next")
    assert r.status_code == 200
    q = r.json()
    # First submission advances the session index
    r = await client.post(f"/api/sessions/{sid}/answer",
        json={"question_id": q["id"], "selected_options": ["A"],
              "confidence": "good", "response_time_ms": 1000},
    )
    assert r.status_code == 200
    # Second submission with the same question_id is now stale → 409
    r = await client.post(f"/api/sessions/{sid}/answer",
        json={"question_id": q["id"], "selected_options": ["A"],
              "confidence": "good", "response_time_ms": 1000},
    )
    assert r.status_code == 409
