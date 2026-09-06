"""Study sessions router — start, answer, complete."""
import asyncio
from contextlib import asynccontextmanager
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from datetime import datetime, timezone
from ..models import (
    SessionStartRequest, SessionStartResponse, AnswerRequest,
    AnswerResponse, SessionSummary, QuestionResponse,
)
from ..database import get_db
from ..guest import get_current_player
from ..services.sr_scheduler import compute_next_review, select_session_questions
from ..services.grading import is_correct_answer, normalize_selection, is_multi_answer as _is_multi
from ..services.challenge import (
    ChallengePoolError,
    save_best_challenge,
    select_challenge_questions,
)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

_session_cache: dict[int, dict] = {}


@asynccontextmanager
async def _locked_session(session_id: int, user_id: int):
    """Serialize mutations of a session in the existing in-process cache."""
    cache = _session_cache.get(session_id)
    if not cache or cache["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    async with cache["lock"]:
        # Completion may have removed the session while this request waited.
        if _session_cache.get(session_id) is not cache:
            raise HTTPException(status_code=404, detail="Session not found")
        yield cache


@router.post("/start", response_model=SessionStartResponse)
async def start_session(
    data: SessionStartRequest,
    current_user: dict = Depends(get_current_player),
):
    async with get_db() as db:
        if data.domain:
            cursor = await db.execute(
                "SELECT * FROM questions WHERE domain = ? AND domain BETWEEN 1 AND 7",
                (data.domain,)
            )
        else:
            cursor = await db.execute("SELECT * FROM questions WHERE domain BETWEEN 1 AND 7")
        all_questions = [dict(r) for r in await cursor.fetchall()]

        if not all_questions:
            raise HTTPException(status_code=404, detail="No questions found for this domain")

        qids = [q["id"] for q in all_questions]
        placeholders = ",".join("?" * len(qids))
        cursor = await db.execute(
            # Exclude the progress row's own ID so merging cannot replace q.id.
            "SELECT question_id, attempts, correct_count, consecutive_correct, "
            "ease_factor, interval_days, next_review_date, mastered, mastered_at, last_attempt_at "
            f"FROM user_progress WHERE user_id = ? AND question_id IN ({placeholders})",
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
            "session_type": data.session_type,
            "lock": asyncio.Lock(),
        }

        return SessionStartResponse(
            session_id=session_id,
            total_questions=len(selected),
            session_type=data.session_type,
        )


@router.post("/challenge", response_model=SessionStartResponse)
async def start_challenge(
    request: Request,
    current_user: dict = Depends(get_current_player),
):
    if await request.body():
        raise HTTPException(
            status_code=422,
            detail="Challenge size and domains are fixed by the server",
        )

    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM questions WHERE domain BETWEEN 1 AND 7"
        )
        try:
            selected = select_challenge_questions(
                [dict(row) for row in await cursor.fetchall()]
            )
        except ChallengePoolError as error:
            raise HTTPException(
                status_code=503,
                detail=f"Challenge question pools are incomplete: {error.missing}",
            )

        cursor = await db.execute(
            "INSERT INTO study_sessions(user_id,domain,session_type) VALUES(?,NULL,'challenge')",
            (current_user["id"],),
        )
        await db.commit()
        session_id = cursor.lastrowid

    _session_cache[session_id] = {
        "user_id": current_user["id"],
        "questions": selected,
        "index": 0,
        "correct_count": 0,
        "session_type": "challenge",
        "lock": asyncio.Lock(),
    }
    return SessionStartResponse(
        session_id=session_id,
        total_questions=20,
        session_type="challenge",
    )


@router.get("/{session_id}/next", response_model=QuestionResponse)
async def get_next_question(
    session_id: int,
    current_user: dict = Depends(get_current_player),
):
    cache = _session_cache.get(session_id)
    if not cache or cache["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Session not found")

    idx = cache["index"]
    if idx >= len(cache["questions"]):
        return Response(status_code=204)

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
        option_e=q.get("option_e"),
        option_f=q.get("option_f"),
        option_g=q.get("option_g"),
        is_multi_answer=_is_multi(q.get("correct_option", "")),
    )


@router.post("/{session_id}/answer", response_model=AnswerResponse)
async def answer_question(
    session_id: int,
    data: AnswerRequest,
    current_user: dict = Depends(get_current_player),
):
    async with _locked_session(session_id, current_user["id"]) as cache:
        return await _answer_current_question(session_id, data, current_user, cache)


async def _answer_current_question(session_id: int, data: AnswerRequest, current_user: dict, cache: dict):
    idx = cache["index"]
    if idx >= len(cache["questions"]):
        raise HTTPException(status_code=409, detail="No unanswered questions remain in this session")
    q = cache["questions"][idx]

    # Prevent submitting the same question twice (e.g. double-tap on frontend).
    # If the question_id doesn't match the current cache question, the session
    # has already moved on — reject the stale submission.
    if q["id"] != data.question_id:
        raise HTTPException(
            status_code=409,
            detail="Submitted question is not the current unanswered question"
        )

    correct_option = q.get("correct_option", "")

    # Normalize user selection and compare
    try:
        user_canonical = normalize_selection(data.selected_options)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid selection: must be at least one option letter from A–G")

    if any(not q.get(f"option_{letter.lower()}") for letter in user_canonical):
        raise HTTPException(status_code=422, detail="Selected option is not available for this question")

    is_correct = is_correct_answer(user_canonical, correct_option)

    async with get_db() as db:
        # Other open sessions may have changed this question's learning state.
        # Serialize the read and update so a stale session cannot restore a streak.
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute(
            "SELECT * FROM user_progress WHERE user_id = ? AND question_id = ?",
            (current_user["id"], q["id"])
        )
        existing = await cursor.fetchone()
        progress = dict(existing) if existing else {}
        sr = compute_next_review(
            data.confidence,
            progress.get("ease_factor", 2.5),
            progress.get("interval_days", 1),
            progress.get("consecutive_correct", 0),
            is_correct=is_correct,
        )
        mastered_at = (progress.get("mastered_at") or sr.mastered_at) if sr.mastered else None

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
                    mastered_at = ?,
                    last_attempt_at = ?
                WHERE user_id = ? AND question_id = ?
            """, (
                1 if is_correct else 0,
                sr.consecutive_correct,
                sr.ease_factor,
                sr.interval_days,
                sr.next_review_date.isoformat(),
                1 if sr.mastered else 0,
                mastered_at,
                datetime.now(timezone.utc).isoformat(),
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
                mastered_at,
                datetime.now(timezone.utc).isoformat(),
            ))

        await db.execute("""
            INSERT INTO user_responses
                (user_id, question_id, session_id, selected_option, is_correct, confidence, response_time_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            current_user["id"], q["id"], session_id,
            user_canonical, is_correct, data.confidence, data.response_time_ms
        ))

        await db.commit()

        # Publish the committed result together, before releasing the session lock.
        if is_correct:
            cache["correct_count"] += 1
        cache["index"] += 1

    return AnswerResponse(
        is_correct=is_correct,
        correct_option=correct_option,
        user_selection=user_canonical,
        explanation=q["explanation"],
        ocg_chapter_ref=q.get("ocg_chapter_ref"),
        ocg_section_ref=q.get("ocg_section_ref"),
        mastered=sr.mastered,
        next_review_days=sr.interval_days,
    )


@router.post(
    "/{session_id}/complete",
    response_model=SessionSummary,
    response_model_exclude_none=True,
)
async def complete_session(
    session_id: int,
    current_user: dict = Depends(get_current_player),
):
    async with _locked_session(session_id, current_user["id"]) as cache:
        return await _complete_locked_session(session_id, cache)


async def _complete_locked_session(session_id: int, cache: dict):
    completed_at = datetime.now(timezone.utc)
    questions_shown = cache["index"]
    correct_count = cache["correct_count"]
    is_challenge = cache.get("session_type") == "challenge"
    if is_challenge and questions_shown != 20:
        raise HTTPException(
            status_code=409,
            detail="Answer all 20 challenge questions before completing",
        )
    accuracy = round(correct_count / questions_shown * 100, 1) if questions_shown > 0 else 0.0
    challenge_record = None

    async with get_db() as db:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "UPDATE study_sessions SET completed_at = ?, questions_shown = ?, correct_count = ? WHERE id = ?",
            (completed_at.isoformat(), questions_shown, correct_count, session_id)
        )
        if is_challenge:
            challenge_record = await save_best_challenge(
                db,
                user_id=cache["user_id"],
                correct_count=correct_count,
                completed_at=completed_at,
            )
        await db.commit()

    del _session_cache[session_id]

    return SessionSummary(
        session_id=session_id,
        questions_shown=questions_shown,
        correct_count=correct_count,
        accuracy_pct=accuracy,
        completed_at=completed_at,
        score=challenge_record["score"] if challenge_record else None,
        wrong_count=challenge_record["wrong_count"] if challenge_record else None,
        rank=challenge_record["rank"] if challenge_record else None,
    )
