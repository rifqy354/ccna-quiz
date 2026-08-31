import pytest
from app.services.sr_scheduler import compute_next_review, MASTERY_THRESHOLD, MIN_EASE, INITIAL_EASE


class TestComputeNextReview:
    def test_again_resets_interval(self):
        result = compute_next_review("again", 2.5, 10, 4)
        assert result.interval_days == 1
        assert result.consecutive_correct == 0
        assert result.mastered is False

    def test_again_decreases_ease(self):
        result = compute_next_review("again", 2.5, 5, 3)
        assert result.ease_factor == 2.3  # 2.5 - 0.2

    def test_again_at_min_ease(self):
        result = compute_next_review("again", MIN_EASE, 1, 0)
        assert result.ease_factor == MIN_EASE  # cannot go below

    def test_good_from_new(self):
        result = compute_next_review("good", INITIAL_EASE, 1, 0)
        assert result.interval_days == 2  # round(1 * 2.5) = round(2.5) = 2 (banker's rounding)
        assert result.consecutive_correct == 1
        assert result.mastered is False

    def test_hard_decreases_ease(self):
        result = compute_next_review("hard", 2.5, 5, 2)
        assert result.ease_factor == 2.35  # 2.5 - 0.15
        assert result.interval_days == 10  # round(5 * 2.5 * 0.8)

    def test_easy_increases_ease(self):
        result = compute_next_review("easy", 2.5, 1, 0)
        assert result.ease_factor == 2.65  # 2.5 + 0.15
        assert result.interval_days == 3  # round(1 * 2.5 * 1.3)

    def test_five_consecutive_good_achieves_mastery(self):
        ease, interval, consecutive = INITIAL_EASE, 1, 0
        for i in range(5):
            result = compute_next_review("good", ease, interval, consecutive)
            ease = result.ease_factor
            interval = result.interval_days
            consecutive = result.consecutive_correct
        assert result.mastered is True
        assert consecutive >= MASTERY_THRESHOLD

    def test_wrong_answer_resets_mastery(self):
        # Start mastered
        result = compute_next_review("good", 2.5, 1, 0)
        for _ in range(4):
            result = compute_next_review("good", result.ease_factor, result.interval_days, result.consecutive_correct)
        assert result.mastered is True
        # Now answer "again"
        result2 = compute_next_review("again", result.ease_factor, result.interval_days, result.consecutive_correct)
        assert result2.mastered is False
        assert result2.consecutive_correct == 0

    def test_next_review_date_is_future(self):
        from datetime import date, timedelta
        result = compute_next_review("good", INITIAL_EASE, 1, 0)
        assert result.next_review_date >= date.today()
        assert result.next_review_date <= date.today() + timedelta(days=10)

    def test_interval_minimum_1_day(self):
        result = compute_next_review("hard", 1.3, 1, 0)
        assert result.interval_days >= 1
