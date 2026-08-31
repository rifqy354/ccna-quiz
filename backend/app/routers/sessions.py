"""Study sessions router — start, answer, complete."""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from ..models import (
    SessionStartRequest, SessionStartResponse, AnswerRequest,
    AnswerResponse, SessionSummary, QuestionResponse,
)
from ..database import get_db
from ..auth import get_current_user
from ..services.sr_scheduler import compute_next_review, select_session_questions

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

_session_cache: dict[int, dict] = {}


@router.post("/start", response_model=SessionStartResponse)
async def start_session(
    data: SessionStartRequest,
    current_user: dict = Depends(get_current_user),
):
    async with get_db() as db:
        if data.domain:
            cursor = await db.execute(
                "SELECT * FROM questions WHERE domain = ? AND domain BETWEEN 1 AND 6",
                (data.domain,)
            )
        else:
            cursor = await db.execute("SELECT * FROM questions WHERE domain BETWEEN 1 AND 6")
        all_questions = [dict(r) for r in await cursor.fetchall()]

        if not all_questions:
            raise HTTPException(status_code=404, detail="No questions found for this domain")

        qids = [q["id"] for q in all_questions]
        placeholders = ",".join("?" * len(qids))
        cursor = await db.execute(
            f"SELECT * FROM user_progress WHERE user_id = ? AND question_id IN ({placeholders})",
            [current_user["id"]] + qids
        )
        progress_map = {r["question_id"]: dict(r) for r in await cursor.fetchall()}

        for q in all_questions:
            q.update(progress_map.get(q["id"], {}))

        selected = select_session_questions(
            current_user["id"], data.domain, data.session_type, data.count, all_questions
        )

        cursor = await db.execute(
            "INSERT INTO study_sessions (user_id, domain, session_type) VALUES (?, ?, ?)",
            (current_user["id"], data.domain, data.session_type)
        )
        await db.commit()
        session_id = cursor.lastrowid

        _session_cache[session_id] = {
            "user_id": current_user["id"],
            "questions": selected,
            "index": 0,
            "correct_count": 0,
        }

        return SessionStartResponse(
            session_id=session_id,
            total_questions=len(selected),
            session_type=data.session_type,
        )


@router.get("/{session_id}/next", response_model=QuestionResponse)
async def get_next_question(
    session_id: int,
    current_user: dict = Depends(get_current_user),
):
    cache = _session_cache.get(session_id)
    if not cache or cache["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Session not found")

    idx = cache["index"]
    if idx >= len(cache["questions"]):
        raise HTTPException(status_code=200, detail="No more questions")

    q = cache["questions"][idx]
    return QuestionResponse(
        id=q["id"],
        source_book=q["source_book"],
        source_chapter=q["source_chapter"],
        book_title=q["book_title"],
        domain=q.get("domain"),
        sub_domain=q.get("sub_domain"),
        sub_domain_name=q.get("sub_domain_name"),
        question_text=q["question_text"],
        question_image=q.get("question_image"),
        option_a=q["option_a"],
        option_b=q["option_b"],
        option_c=q["option_c"],
        option_d=q["option_d"],
    )


@router.post("/{session_id}/answer", response_model=AnswerResponse)
async def answer_question(
    session_id: int,
    data: AnswerRequest,
    current_user: dict = Depends(get_current_user),
):
    cache = _session_cache.get(session_id)
    if not cache or cache["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Session not found")

    idx = cache["index"]
    q = cache["questions"][idx]

    is_correct = data.selected_option == q["correct_option"]

    current_progress = {
        "ease_factor": q.get("ease_factor", 2.5),
        "interval_days": q.get("interval_days", 1),
        "consecutive_correct": q.get("consecutive_correct", 0),
    }
    sr = compute_next_review(
        data.confidence,
        current_progress["ease_factor"],
        current_progress["interval_days"],
        current_progress["consecutive_correct"],
    )

    async with get_db() as db:
        from datetime import date as date_cls
        today = date_cls.today().isoformat()

        cursor = await db.execute(
            "SELECT id FROM user_progress WHERE user_id = ? AND question_id = ?",
            (current_user["id"], q["id"])
        )
        existing = await cursor.fetchone()

        if existing:
            await db.execute("""
                UPDATE user_progress SET
                    attempts = attempts + 1,
                    correct_count = correct_count + ?,
                    consecutive_correct = ?,
                    ease_factor = ?,
                    interval_days = ?,
                    next_review_date = ?,
                    mastered = ?,
                    mastered_at = COALESCE(mastered_at, ?),
                    last_attempt_at = ?
                WHERE user_id = ? AND question_id = ?
            """, (
                1 if is_correct else 0,
                sr.consecutive_correct,
                sr.ease_factor,
                sr.interval_days,
                sr.next_review_date.isoformat(),
                1 if sr.mastered else 0,
                sr.mastered_at,
                datetime.utcnow().isoformat(),
                current_user["id"],
                q["id"],
            ))
        else:
            await db.execute("""
                INSERT INTO user_progress
                    (user_id, question_id, attempts, correct_count, consecutive_correct,
                     ease_factor, interval_days, next_review_date, mastered, mastered_at, last_attempt_at)
                VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                current_user["id"], q["id"],
                1 if is_correct else 0,
                sr.consecutive_correct,
                sr.ease_factor,
                sr.interval_days,
                sr.next_review_date.isoformat(),
                1 if sr.mastered else 0,
                sr.mastered_at,
                datetime.utcnow().isoformat(),
            ))

        await db.execute("""
            INSERT INTO user_responses
                (user_id, question_id, session_id, selected_option, is_correct, confidence, response_time_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            current_user["id"], q["id"], session_id,
            data.selected_option, is_correct, data.confidence, data.response_time_ms
        ))

        if is_correct:
            cache["correct_count"] += 1

        await db.commit()

    return AnswerResponse(
        is_correct=is_correct,
        correct_option=q["correct_option"],
        explanation=q["explanation"],
        ocg_chapter_ref=q.get("ocg_chapter_ref"),
        ocg_section_ref=q.get("ocg_section_ref"),
        mastered=sr.mastered,
        next_review_days=sr.interval_days,
    )


@router.post("/{session_id}/complete", response_model=SessionSummary)
async def complete_session(
    session_id: int,
    current_user: dict = Depends(get_current_user),
):
    cache = _session_cache.get(session_id)
    if not cache or cache["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Session not found")

    completed_at = datetime.utcnow()
    questions_shown = len(cache["questions"])
    correct_count = cache["correct_count"]
    accuracy = round(correct_count / questions_shown * 100, 1) if questions_shown > 0 else 0.0

    async with get_db() as db:
        await db.execute(
            "UPDATE study_sessions SET completed_at = ?, questions_shown = ?, correct_count = ? WHERE id = ?",
            (completed_at.isoformat(), questions_shown, correct_count, session_id)
        )
        await db.commit()

    del _session_cache[session_id]

    return SessionSummary(
        session_id=session_id,
        questions_shown=questions_shown,
        correct_count=correct_count,
        accuracy_pct=accuracy,
        completed_at=completed_at,
    )
