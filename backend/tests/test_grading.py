"""Tests for multi-answer question support."""
import pytest
from app.services.grading import (
    normalize_selection,
    is_multi_answer,
    is_correct_answer,
    GRADING_LETTERS,
)


class TestNormalizeSelection:
    """Canonicalization: uppercase, deduplicate, sort, reject invalid."""

    def test_uppercase(self):
        assert normalize_selection(["c", "b", "a"]) == "ABC"

    def test_dedup(self):
        assert normalize_selection(["A", "A", "B", "A"]) == "AB"

    def test_order_independent(self):
        assert normalize_selection(["D", "B", "A", "C"]) == "ABCD"
        assert normalize_selection(["G", "A", "D", "F"]) == "ADFG"

    def test_single(self):
        assert normalize_selection(["C"]) == "C"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="at least one"):
            normalize_selection([])

    def test_invalid_letter_raises(self):
        with pytest.raises(ValueError, match="invalid letter"):
            normalize_selection(["A", "X"])

    def test_lowercase_input(self):
        assert normalize_selection(["a", "b", "c", "d"]) == "ABCD"

    def test_none_input_raises(self):
        with pytest.raises(ValueError, match="at least one"):
            normalize_selection(None)

    def test_legacy_single_string_a(self):
        """Legacy single-string format 'A' should normalize to 'A'."""
        assert normalize_selection("A") == "A"

    def test_legacy_single_string_lowercase(self):
        assert normalize_selection("c") == "C"

    def test_legacy_string_raises_if_invalid(self):
        with pytest.raises(ValueError, match="invalid letter"):
            normalize_selection("AX")


class TestIsMultiAnswer:
    """Determine whether a question expects multiple selections."""

    def test_single_letter_is_not_multi(self):
        assert is_multi_answer("A") is False
        assert is_multi_answer("C") is False

    def test_two_letters_is_multi(self):
        assert is_multi_answer("AB") is True
        assert is_multi_answer("DF") is True

    def test_three_letters_is_multi(self):
        assert is_multi_answer("BDE") is True
        assert is_multi_answer("ABC") is True

    def test_four_letters_is_multi(self):
        assert is_multi_answer("ABCF") is True

    def test_all_valid_letters(self):
        assert is_multi_answer("ABCD") is True


class TestIsCorrectAnswer:
    """Set-equality grading — exact match required."""

    # ── Single-answer ──────────────────────────────────────────────────────────
    def test_single_correct_exact(self):
        assert is_correct_answer("C", "C") is True

    def test_single_incorrect_wrong_letter(self):
        assert is_correct_answer("B", "C") is False

    def test_single_incorrect_vs_multi(self):
        """Single selected on a multi-answer question = incorrect."""
        assert is_correct_answer("B", "BDE") is False

    # ── Multi-answer: exact match ──────────────────────────────────────────────
    def test_multi_correct_exact_order(self):
        assert is_correct_answer("BDE", "BDE") is True

    def test_multi_correct_different_order(self):
        # Real DB values: "BDE", "DF", "AG"
        assert is_correct_answer("DCB", "BCD") is True
        assert is_correct_answer("DF", "FD") is True
        assert is_correct_answer("AG", "GA") is True

    def test_multi_correct_uppercase_lowercase(self):
        assert is_correct_answer("bcd", "BCD") is True
        assert is_correct_answer("df", "DF") is True

    # ── Multi-answer: partial ──────────────────────────────────────────────────
    def test_multi_partial_too_few(self):
        assert is_correct_answer("BD", "BDE") is False

    def test_multi_partial_superset(self):
        assert is_correct_answer("BDEA", "BDE") is False

    def test_multi_partial_subset(self):
        assert is_correct_answer("AB", "ABD") is False

    # ── Multi-answer: wrong letters ────────────────────────────────────────────
    def test_multi_wrong_letter(self):
        assert is_correct_answer("BCF", "BDE") is False

    def test_multi_complete_different(self):
        assert is_correct_answer("ABC", "DEF") is False

    # ── Edge cases ────────────────────────────────────────────────────────────
    def test_empty_selected_vs_any_correct(self):
        """Empty selection cannot match any non-empty correct."""
        assert is_correct_answer("", "A") is False

    def test_grading_letters_constant(self):
        """A-G are valid for grading (OCG has up to 7 options in some questions)."""
        assert set(GRADING_LETTERS) == {"A", "B", "C", "D", "E", "F", "G"}
