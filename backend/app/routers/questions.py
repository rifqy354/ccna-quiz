"""Questions and domains router."""
from fastapi import APIRouter, Depends, Query, HTTPException
from ..models import DomainSummary, QuestionResponse
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/api", tags=["questions"])

DOMAIN_NAMES = {
    1: "Network Fundamentals",
    2: "Network Access",
    3: "IP Connectivity",
    4: "IP Services",
    5: "Security Fundamentals",
    6: "Automation and Programmability",
}


@router.get("/domains", response_model=list[DomainSummary])
async def list_domains(
    current_user: dict = Depends(get_current_user),
):
    async with get_db() as db:
        results = []
        for domain_num in range(1, 7):
            cursor = await db.execute(
                "SELECT COUNT(*) as cnt FROM questions WHERE domain = ?", (domain_num,)
            )
            row = await cursor.fetchone()
            total = row[0] if row else 0

            cursor = await db.execute("""
                SELECT
                    COUNT(CASE WHEN up.mastered = 1 THEN 1 END) as mastered,
                    COUNT(CASE WHEN up.attempts > 0 THEN 1 END) as attempted
                FROM user_progress up
                JOIN questions q ON q.id = up.question_id
                WHERE up.user_id = ? AND q.domain = ?
            """, (current_user["id"], domain_num))
            row = await cursor.fetchone()
            mastered = row[0] if row else 0
            attempted = row[1] if row else 0

            results.append(DomainSummary(
                domain=domain_num,
                name=DOMAIN_NAMES.get(domain_num, f"Domain {domain_num}"),
                total_questions=total,
                mastered=mastered,
                attempted=attempted,
            ))
        return results


@router.get("/domains/{domain_id}", response_model=dict)
async def get_domain(
    domain_id: int,
    current_user: dict = Depends(get_current_user),
):
    if domain_id < 1 or domain_id > 6:
        raise HTTPException(status_code=404, detail="Domain not found")

    async with get_db() as db:
        cursor = await db.execute("""
            SELECT sub_domain, sub_domain_name, COUNT(*) as cnt
            FROM questions
            WHERE domain = ? AND sub_domain IS NOT NULL
            GROUP BY sub_domain, sub_domain_name
            ORDER BY sub_domain
        """, (domain_id,))
        sub_domains = [dict(r) for r in await cursor.fetchall()]

        return {
            "domain": domain_id,
            "name": DOMAIN_NAMES.get(domain_id),
            "sub_domains": sub_domains,
        }


@router.get("/questions/random", response_model=QuestionResponse)
async def get_random_question(
    domain: int = Query(default=None, ge=1, le=6),
    current_user: dict = Depends(get_current_user),
):
    async with get_db() as db:
        if domain:
            cursor = await db.execute(
                "SELECT * FROM questions WHERE domain = ? ORDER BY RANDOM() LIMIT 1",
                (domain,)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM questions ORDER BY RANDOM() LIMIT 1"
            )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No questions found")
        return dict(row)
