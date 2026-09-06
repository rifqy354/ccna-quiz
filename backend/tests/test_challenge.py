from collections import Counter
import random

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.main import app
from app.services.challenge import ChallengePoolError, select_challenge_questions


def test_challenge_has_fixed_domain_distribution():
    questions = [
        {"id": domain * 100 + index, "domain": domain}
        for domain in range(1, 8)
        for index in range(5)
    ]

    selected = select_challenge_questions(questions, random.Random(7))

    assert len(selected) == 20
    assert Counter(question["domain"] for question in selected) == {
        1: 3, 2: 3, 3: 3, 4: 3, 5: 3, 6: 3, 7: 2,
    }
    assert len({question["id"] for question in selected}) == 20


def test_challenge_reports_every_undersized_pool():
    questions = [
        {"id": domain * 100 + index, "domain": domain}
        for domain in range(1, 8)
        for index in range(2)
    ]

    with pytest.raises(ChallengePoolError) as error:
        select_challenge_questions(questions, random.Random(7))

    assert error.value.missing == {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1}


@pytest_asyncio.fixture
async def challenge_client():
    async with get_db() as db:
        for domain in range(1, 8):
            count = (
                await (
                    await db.execute(
                        "SELECT COUNT(*) FROM questions WHERE domain=?", (domain,)
                    )
                ).fetchone()
            )[0]
            required = 3 if domain <= 6 else 2
            for index in range(count, required):
                await db.execute(
                    """
                    INSERT INTO questions(
                        source_book,source_chapter,book_title,domain,sub_domain,
                        sub_domain_name,question_text,option_a,option_b,option_c,
                        option_d,correct_option,explanation
                    ) VALUES('challenge','ch1','Challenge',?,'topic','Topic',?,
                             'A','B','C','D','A','Explanation')
                    """,
                    (domain, f"Domain {domain} question {index}"),
                )
        await db.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://test"
    ) as client:
        created = await client.post("/api/player", json={"name": "Challenger"})
        assert created.status_code == 201
        yield client


async def _answer_current(client: AsyncClient, session_id: int, correctly: bool):
    question = await client.get(f"/api/sessions/{session_id}/next")
    assert question.status_code == 200
    question_id = question.json()["id"]
    async with get_db() as db:
        correct = (
            await (
                await db.execute(
                    "SELECT correct_option FROM questions WHERE id=?", (question_id,)
                )
            ).fetchone()
        )[0]
    selected = list(correct) if correctly else (["B"] if correct != "B" else ["A"])
    answered = await client.post(
        f"/api/sessions/{session_id}/answer",
        json={
            "question_id": question_id,
            "selected_options": selected,
            "confidence": "good",
        },
    )
    assert answered.status_code == 200


@pytest.mark.asyncio
async def test_challenge_endpoint_reports_incomplete_question_pools():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://test"
    ) as client:
        assert (await client.post("/api/player", json={"name": "Pool Test"})).status_code == 201
        response = await client.post("/api/sessions/challenge")
    assert response.status_code == 503
    assert response.json()["detail"].startswith("Challenge question pools are incomplete")


@pytest.mark.asyncio
async def test_challenge_start_is_fixed_and_rejects_client_sizing(challenge_client):
    rejected = await challenge_client.post(
        "/api/sessions/challenge", json={"count": 5, "domain": 1}
    )
    assert rejected.status_code == 422

    started = await challenge_client.post("/api/sessions/challenge")
    assert started.status_code == 200
    assert started.json()["total_questions"] == 20
    assert started.json()["session_type"] == "challenge"

    session_id = started.json()["session_id"]
    domains = []
    for _ in range(20):
        question = await challenge_client.get(f"/api/sessions/{session_id}/next")
        domains.append(question.json()["domain"])
        await _answer_current(challenge_client, session_id, correctly=True)
    assert Counter(domains) == {1: 3, 2: 3, 3: 3, 4: 3, 5: 3, 6: 3, 7: 2}


@pytest.mark.asyncio
async def test_partial_challenge_cannot_complete_or_create_record(challenge_client):
    started = await challenge_client.post("/api/sessions/challenge")
    session_id = started.json()["session_id"]
    await _answer_current(challenge_client, session_id, correctly=True)

    partial = await challenge_client.post(f"/api/sessions/{session_id}/complete")
    assert partial.status_code == 409
    async with get_db() as db:
        count = await (await db.execute("SELECT COUNT(*) FROM challenge_records")).fetchone()
    assert count[0] == 0


@pytest.mark.asyncio
async def test_completed_challenge_returns_backend_score_and_record(challenge_client):
    started = await challenge_client.post("/api/sessions/challenge")
    session_id = started.json()["session_id"]
    for index in range(20):
        await _answer_current(challenge_client, session_id, correctly=index < 17)

    completed = await challenge_client.post(f"/api/sessions/{session_id}/complete")

    assert completed.status_code == 200
    assert completed.json()["questions_shown"] == 20
    assert completed.json()["correct_count"] == 17
    assert completed.json()["score"] == 85
    assert completed.json()["wrong_count"] == 3
    assert completed.json()["rank"] == 1
    async with get_db() as db:
        record = await (await db.execute("SELECT * FROM challenge_records")).fetchone()
    assert record["score"] == 85
    assert record["correct_count"] == 17
    assert record["wrong_count"] == 3


@pytest.mark.asyncio
async def test_regular_study_completion_never_creates_challenge_record(challenge_client):
    started = await challenge_client.post(
        "/api/sessions/start", json={"session_type": "mixed", "count": 1}
    )
    await _answer_current(challenge_client, started.json()["session_id"], correctly=True)
    completed = await challenge_client.post(
        f"/api/sessions/{started.json()['session_id']}/complete"
    )
    assert completed.status_code == 200
    assert "score" not in completed.json()
    async with get_db() as db:
        count = await (await db.execute("SELECT COUNT(*) FROM challenge_records")).fetchone()
    assert count[0] == 0
