"""Statistics regressions against the suite's disposable database."""
from datetime import date, timedelta

import pytest
import pytest_asyncio

from app.database import get_db
from app.services.mastery import get_study_streak, get_weak_areas
from app.routers.stats import dashboard


@pytest_asyncio.fixture
async def user():
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO users(email,password_hash,name) VALUES('stats@example.com','unused','Stats')"
        )
        await db.commit()
        return {'id': cursor.lastrowid}


@pytest.mark.asyncio
@pytest.mark.parametrize('days,expected', [([0, 2, 4], 1), ([1, 3], 1), ([0, 1, 2], 3), ([1, 2], 2), ([2], 0), ([], 0)])
async def test_streak_requires_consecutive_days(user, days, expected):
    async with get_db() as db:
        await db.executemany(
            "INSERT INTO study_sessions(user_id,session_type,completed_at,questions_shown) VALUES(?,'mixed',?,1)",
            [(user['id'], (date.today() - timedelta(days=day)).isoformat()) for day in days],
        )
        await db.commit()
    assert await get_study_streak(user['id']) == expected


async def test_empty_completed_session_does_not_earn_streak(user):
    async with get_db() as db:
        await db.execute(
            "INSERT INTO study_sessions(user_id,session_type,completed_at,questions_shown) VALUES(?,'mixed',?,0)",
            (user['id'], date.today().isoformat()),
        )
        await db.commit()
    assert await get_study_streak(user['id']) == 0


@pytest.mark.asyncio
async def test_weak_areas_keep_book_topics_separate(user):
    async with get_db() as db:
        await db.execute("UPDATE questions SET sub_domain='ch01_q1', sub_domain_name='Shared chapter', domain=1 WHERE id IN (1,2)")
        await db.execute("UPDATE questions SET source_book='volume-1' WHERE id=1")
        await db.execute("UPDATE questions SET source_book='volume-2' WHERE id=2")
        await db.executemany(
            'INSERT INTO user_progress(user_id,question_id,attempts,correct_count) VALUES(?,?,1,?)',
            [(user['id'], 1, 0), (user['id'], 2, 1)],
        )
        await db.commit()
    areas = await get_weak_areas(user['id'])
    assert len(areas) == 1
    assert areas[0]['correct'] == 0
    assert areas[0]['total'] == 1
    assert areas[0]['source_book'] == 'volume-1'


@pytest.mark.asyncio
async def test_dashboard_keeps_exact_mastered_count(user):
    async with get_db() as db:
        await db.executemany(
            "INSERT INTO questions(source_book,source_chapter,book_title,domain,question_text,option_a,option_b,option_c,option_d,correct_option,explanation) VALUES('test','ch1','Test',1,'Q','a','b','c','d','A','E')",
            [() for _ in range(2000)],
        )
        await db.execute('INSERT INTO user_progress(user_id,question_id,attempts,correct_count,mastered) VALUES(?,1,1,1,1)', (user['id'],))
        await db.commit()
    result = await dashboard(user)
    assert result.questions_mastered == 1
    assert result.domains[0].mastered == 1


@pytest.mark.asyncio
async def test_dashboard_excludes_unavailable_question_progress(user):
    async with get_db() as db:
        await db.execute('UPDATE questions SET domain=0 WHERE id=1')
        await db.execute(
            'INSERT INTO user_progress(user_id,question_id,attempts,correct_count,mastered,next_review_date) VALUES(?,1,1,1,1,?)',
            (user['id'], date.today().isoformat()),
        )
        await db.commit()
    result = await dashboard(user)
    assert result.total_questions == 6
    assert result.questions_mastered == 0
    assert result.questions_attempted == 0
    assert result.overall_recall_rate == 0
    assert result.due_today == 0
