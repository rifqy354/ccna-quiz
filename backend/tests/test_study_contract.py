"""Study contracts exercised against a temporary question bank."""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.auth import get_current_user
from app.main import app
from app.routers import sessions
from app import database
from app.services.sr_scheduler import select_session_questions


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
async def test_random_reports_multiple_answers_without_revealing_key(returning_learner):
    async with database.get_db() as db:
        await db.execute("UPDATE questions SET correct_option = 'DF'")
        await db.commit()
    response = await returning_learner.get('/api/questions/random')
    assert response.status_code == 200
    assert response.json()['is_multi_answer'] is True
    assert 'correct_option' not in response.json()


@pytest.mark.asyncio
async def test_completion_counts_only_answers_and_exhaustion_has_no_body(returning_learner):
    client = returning_learner
    started = await client.post('/api/sessions/start', json={'count': 2})
    sid = started.json()['session_id']
    answer = await client.post(f'/api/sessions/{sid}/answer', json={
        'question_id': 101, 'selected_options': ['D', 'F'], 'confidence': 'good'})
    assert answer.status_code == 200
    complete = await client.post(f'/api/sessions/{sid}/complete')
    assert complete.json()['questions_shown'] == 1
    assert complete.json()['accuracy_pct'] == 100
    started = await client.post('/api/sessions/start', json={'session_type': 'new', 'count': 1})
    sid = started.json()['session_id']
    await client.post(f'/api/sessions/{sid}/answer', json={
        'question_id': 7, 'selected_options': ['A'], 'confidence': 'good'})
    exhausted = await client.get(f'/api/sessions/{sid}/next')
    assert exhausted.status_code == 204
    assert exhausted.content == b''


@pytest.mark.asyncio
@pytest.mark.parametrize('changes', [
    {'question_id': 0}, {'response_time_ms': -1}, {'selected_options': ['G']},
])
async def test_invalid_answer_does_not_advance_or_write(returning_learner, changes):
    client = returning_learner
    started = await client.post('/api/sessions/start', json={'session_type': 'review', 'count': 1})
    sid = started.json()['session_id']
    payload = {'question_id': 101, 'selected_options': ['D'], 'confidence': 'good'}
    response = await client.post(f'/api/sessions/{sid}/answer', json=payload | changes)
    assert response.status_code == 422
    assert (await client.get(f'/api/sessions/{sid}/next')).json()['id'] == 101
    async with database.get_db() as db:
        cursor = await db.execute('SELECT COUNT(*) FROM user_responses')
        assert (await cursor.fetchone())[0] == 0


@pytest.mark.asyncio
async def test_unknown_session_type_rejected(returning_learner):
    response = await returning_learner.post('/api/sessions/start', json={'session_type': 'typo'})
    assert response.status_code == 422


def test_review_never_duplicates_due_mastered_and_includes_learning():
    rows = [
        {'id': 1, 'attempts': 5, 'mastered': 1, 'next_review_date': '2000-01-01', 'last_attempt_at': '2000-01-01'},
        {'id': 2, 'attempts': 1, 'mastered': 0, 'next_review_date': '9999-01-01'},
    ]
    assert [q['id'] for q in select_session_questions(1, None, 'review', 3, rows)] == [1, 2]


def test_mixed_one_prioritizes_due_and_fills_with_learning():
    rows = [{'id': 1, 'attempts': 1, 'next_review_date': '2000-01-01'},
            {'id': 2, 'attempts': 1, 'next_review_date': '9999-01-01'}]
    assert [q['id'] for q in select_session_questions(1, None, 'mixed', 1, rows)] == [1]
    assert [q['id'] for q in select_session_questions(1, None, 'mixed', 5, rows)] == [1, 2]
    assert select_session_questions(1, None, 'new', 5, rows) == []
