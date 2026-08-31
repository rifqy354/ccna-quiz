"""SM-2 variant spaced repetition scheduler."""
from datetime import date, timedelta
from dataclasses import dataclass
from typing import Literal

Confidence = Literal["again", "hard", "good", "easy"]
MASTERY_THRESHOLD = 5
MIN_EASE = 1.3
INITIAL_EASE = 2.5


@dataclass
class SRResult:
    ease_factor: float
    interval_days: int
    next_review_date: date
    consecutive_correct: int
    mastered: bool
    mastered_at: str | None


def compute_next_review(
    confidence: Confidence,
    current_ease: float,
    current_interval: int,
    current_consecutive_correct: int,
) -> SRResult:
    """SM-2 variant scheduler.

    Args:
        confidence: User's confidence response
        current_ease: Current ease factor (default 2.5, min 1.3)
        current_interval: Current interval in days (default 1)
        current_consecutive_correct: Number of consecutive correct answers

    Returns:
        SRResult with new state values
    """
    ease = current_ease
    interval = current_interval
    consecutive = current_consecutive_correct

    if confidence == "again":
        interval = 1
        ease = max(MIN_EASE, ease - 0.2)
        consecutive = 0
    elif confidence == "hard":
        interval = max(1, round(interval * ease * 0.8))
        ease = max(MIN_EASE, ease - 0.15)
        consecutive += 1
    elif confidence == "good":
        interval = max(1, round(interval * ease))
        consecutive += 1
    elif confidence == "easy":
        interval = max(1, round(interval * ease * 1.3))
        ease = ease + 0.15
        consecutive += 1

    mastered = consecutive >= MASTERY_THRESHOLD
    mastered_at = date.today().isoformat() if mastered else None
    next_review = date.today() + timedelta(days=interval)

    return SRResult(
        ease_factor=ease,
        interval_days=interval,
        next_review_date=next_review,
        consecutive_correct=consecutive,
        mastered=mastered,
        mastered_at=mastered_at,
    )


def select_session_questions(
    user_id: int,
    domain: int | None,
    session_type: str,
    count: int,
    db_rows: list,
) -> list[dict]:
    """Select questions for a study session based on SR state and session type."""
    today = date.today()

    due = [r for r in db_rows if r.get("next_review_date") and r["next_review_date"] <= str(today)]
    new_qs = [r for r in db_rows if r.get("attempts", 0) == 0]
    mastered_stale = [r for r in db_rows if r.get("mastered") and r.get("last_attempt_at")]
    in_learning = [r for r in db_rows if r.get("attempts", 0) > 0 and not r.get("mastered")]

    selected = []
    remaining = count

    if session_type == "review":
        for q in sorted(due, key=lambda r: r.get("next_review_date", "")):
            if remaining <= 0:
                break
            selected.append(q)
            remaining -= 1
        if remaining > 0:
            for q in mastered_stale[-remaining:]:
                selected.append(q)
                remaining -= 1
    elif session_type == "new":
        for q in new_qs[:count]:
            selected.append(q)
    else:  # mixed
        due_count = min(count // 2, len(due))
        new_count = count - due_count
        for q in sorted(due, key=lambda r: r.get("next_review_date", ""))[:due_count]:
            selected.append(q)
        for q in new_qs[:new_count]:
            selected.append(q)

    return selected
