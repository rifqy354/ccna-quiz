"""Mastery computation service."""
from datetime import date, timedelta
from typing import List
from ..database import get_db


async def compute_domain_mastery(user_id: int) -> dict:
    """Compute mastery stats per domain."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT
                q.domain,
                COUNT(*) as total,
                COUNT(CASE WHEN up.mastered = 1 THEN 1 END) as mastered,
                COUNT(CASE WHEN up.attempts > 0 THEN 1 END) as attempted,
                SUM(CASE WHEN up.attempts > 0 THEN up.correct_count ELSE 0 END) as total_correct,
                SUM(up.attempts) as total_attempts
            FROM questions q
            LEFT JOIN user_progress up ON up.question_id = q.id AND up.user_id = ?
            WHERE q.domain BETWEEN 1 AND 7
            GROUP BY q.domain
        """, (user_id,))
        rows = await cursor.fetchall()

        domains = {}
        for row in rows:
            total = row[1] or 0
            mastered = row[2] or 0
            attempted = row[3] or 0
            total_correct = row[4] or 0
            total_attempts = row[5] or 0
            domains[row[0]] = {
                "mastered": mastered,
                "mastered_pct": round(mastered / total * 100, 1) if total else 0,
                "attempted": attempted,
                "recall_rate": round(total_correct / total_attempts * 100, 1) if total_attempts else 0,
            }
        return domains


async def get_study_streak(user_id: int) -> int:
    """Count consecutive days with at least one study session."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT DISTINCT DATE(completed_at) as study_date
            FROM study_sessions
            WHERE user_id = ? AND completed_at IS NOT NULL AND questions_shown > 0
            ORDER BY study_date DESC
        """, (user_id,))
        rows = await cursor.fetchall()
        if not rows:
            return 0

        streak = 0
        today = date.today()
        expected = date.fromisoformat(rows[0][0])
        if expected not in (today, today - timedelta(days=1)):
            return 0
        for row in rows:
            d = date.fromisoformat(row[0])
            if d == expected:
                streak += 1
                expected = d - timedelta(days=1)
            else:
                break
        return streak


async def get_weak_areas(user_id: int, threshold: float = 60.0) -> List[dict]:
    """Find sub-domains with recall rate below threshold."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT
                q.source_book,
                q.source_chapter,
                q.sub_domain,
                q.sub_domain_name,
                q.domain,
                SUM(up.correct_count) as correct,
                SUM(up.attempts) as total
            FROM questions q
            LEFT JOIN user_progress up ON up.question_id = q.id AND up.user_id = ?
            WHERE q.sub_domain IS NOT NULL AND up.attempts > 0
            GROUP BY q.source_book, q.source_chapter, q.domain, q.sub_domain, q.sub_domain_name
            HAVING total > 0 AND (CAST(correct AS REAL) / total * 100) < ?
            ORDER BY (CAST(correct AS REAL) / total * 100) ASC
            LIMIT 10
        """, (user_id, threshold))
        return [dict(r) for r in await cursor.fetchall()]
