"""Statistics and dashboard router."""
from fastapi import APIRouter, Depends
from datetime import date
from ..models import DashboardStats, DomainSummary
from ..database import get_db
from ..guest import get_current_player
from ..services.mastery import compute_domain_mastery, get_study_streak, get_weak_areas

router = APIRouter(prefix="/api/stats", tags=["stats"])

DOMAIN_NAMES = {
    1: "Network Fundamentals",
    2: "Network Access",
    3: "IP Connectivity",
    4: "IP Services",
    5: "Security Fundamentals",
    6: "Automation and Programmability",
    7: "Practice Exams",
}


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard(
    current_user: dict = Depends(get_current_player),
):
    today = date.today().isoformat()
    user_id = current_user["id"]

    async with get_db() as db:
        cursor = await db.execute("SELECT COUNT(*) FROM questions WHERE domain BETWEEN 1 AND 7")
        total = (await cursor.fetchone())[0]

        cursor = await db.execute("""
            SELECT
                COUNT(CASE WHEN up.mastered = 1 THEN 1 END),
                COUNT(CASE WHEN up.attempts > 0 THEN 1 END),
                COALESCE(SUM(CASE WHEN up.attempts > 0 THEN up.correct_count ELSE 0 END), 0),
                COALESCE(SUM(up.attempts), 0),
                COUNT(CASE WHEN up.next_review_date <= ? THEN 1 END)
            FROM user_progress up
            JOIN questions q ON q.id = up.question_id
            WHERE up.user_id = ? AND q.domain BETWEEN 1 AND 7
        """, (today, user_id))
        mastered, attempted, correct, attempts, due_today = await cursor.fetchone()
        recall_rate = round(correct / attempts * 100, 1) if attempts else 0.0

        domain_stats = await compute_domain_mastery(user_id)
        domains = []
        for d_num in range(1, 8):
            stats = domain_stats.get(d_num, {})
            cursor = await db.execute(
                "SELECT COUNT(*) FROM questions WHERE domain = ?", (d_num,)
            )
            total_d = (await cursor.fetchone())[0]
            domains.append(DomainSummary(
                domain=d_num,
                name=DOMAIN_NAMES.get(d_num, f"Domain {d_num}"),
                total_questions=total_d,
                mastered=stats.get("mastered", 0),
                attempted=stats.get("attempted", 0),
            ))

        streak = await get_study_streak(user_id)

    return DashboardStats(
        total_questions=total,
        questions_mastered=mastered,
        questions_attempted=attempted,
        overall_recall_rate=recall_rate,
        study_streak=streak,
        due_today=due_today,
        domains=domains,
    )


@router.get("/weak-areas")
async def weak_areas(
    threshold: float = 60.0,
    current_user: dict = Depends(get_current_player),
):
    areas = await get_weak_areas(current_user["id"], threshold)
    return {"weak_areas": areas}
