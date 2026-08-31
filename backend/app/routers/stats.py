"""Statistics and dashboard router."""
from fastapi import APIRouter, Depends
from datetime import date
from ..models import DashboardStats, DomainSummary
from ..database import get_db
from ..auth import get_current_user
from ..services.mastery import compute_domain_mastery, get_study_streak, get_weak_areas

router = APIRouter(prefix="/api/stats", tags=["stats"])

DOMAIN_NAMES = {
    1: "Network Fundamentals",
    2: "Network Access",
    3: "IP Connectivity",
    4: "IP Services",
    5: "Security Fundamentals",
    6: "Automation and Programmability",
}


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard(
    current_user: dict = Depends(get_current_user),
):
    today = date.today().isoformat()
    user_id = current_user["id"]

    async with get_db() as db:
        cursor = await db.execute("SELECT COUNT(*) FROM questions WHERE domain BETWEEN 1 AND 6")
        total = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM user_progress WHERE user_id = ? AND mastered = 1",
            (user_id,)
        )
        mastered = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM user_progress WHERE user_id = ? AND attempts > 0",
            (user_id,)
        )
        attempted = (await cursor.fetchone())[0]

        cursor = await db.execute("""
            SELECT SUM(correct_count), SUM(attempts) FROM user_progress
            WHERE user_id = ? AND attempts > 0
        """, (user_id,))
        row = await cursor.fetchone()
        recall_rate = round(row[0] / row[1] * 100, 1) if row[1] else 0.0

        cursor = await db.execute(
            "SELECT COUNT(*) FROM user_progress WHERE user_id = ? AND next_review_date <= ?",
            (user_id, today)
        )
        due_today = (await cursor.fetchone())[0]

        domain_stats = await compute_domain_mastery(user_id)
        domains = []
        for d_num in range(1, 7):
            stats = domain_stats.get(d_num, {})
            cursor = await db.execute(
                "SELECT COUNT(*) FROM questions WHERE domain = ?", (d_num,)
            )
            total_d = (await cursor.fetchone())[0]
            domains.append(DomainSummary(
                domain=d_num,
                name=DOMAIN_NAMES.get(d_num, f"Domain {d_num}"),
                total_questions=total_d,
                mastered=round(stats.get("mastered_pct", 0) / 100 * total_d),
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
    current_user: dict = Depends(get_current_user),
):
    areas = await get_weak_areas(current_user["id"], threshold)
    return {"weak_areas": areas}
