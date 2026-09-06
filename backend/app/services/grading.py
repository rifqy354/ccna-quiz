"""Multi-answer grading and normalization utilities.

Canonicalization rules:
  - Uppercase only
  - Valid letters only (A–D)
  - No duplicates
  - Sorted ascending for deterministic storage
  - Order does not affect correctness
"""
from typing import Union

GRADING_LETTERS = frozenset("ABCDEFG")


def normalize_selection(
    selected: Union[list[str], str, None]
) -> str:
    """Canonicalize a user selection to a sorted uppercase string.

    Args:
        selected: A list of letter strings, or a single string.
        Strings longer than 1 character (e.g. "BDE" from a legacy format or
        stored correct answer) are split into individual letters.

    Returns:
        A sorted uppercase string, e.g. "BDE".

    Raises:
        ValueError: If no selections provided or any letter is outside A–D.
    """
    if selected is None:
        raise ValueError("selected must contain at least one option")

    # Support legacy single-string format: normalize_selection("A") -> "A"
    if isinstance(selected, str):
        if not selected.strip():
            raise ValueError("selected must contain at least one option")
        # Split multi-character strings (e.g. "BDE") into individual letters
        letters = [ch.upper().strip() for ch in selected if ch.strip()]
    else:
        if not selected:
            raise ValueError("selected must contain at least one option")
        letters = [s.upper().strip() for s in selected if s]

    if not letters:
        raise ValueError("selected must contain at least one option")

    # Validate and deduplicate
    seen: set[str] = set()
    result: list[str] = []
    for letter in letters:
        if letter not in GRADING_LETTERS:
            raise ValueError(f"invalid letter '{letter}': must be one of {sorted(GRADING_LETTERS)}")
        if letter not in seen:
            seen.add(letter)
            result.append(letter)

    result.sort()
    return "".join(result)


def is_multi_answer(correct_option: str) -> bool:
    """Return True when the correct answer requires multiple selections."""
    if not correct_option:
        return False
    return len(correct_option.strip()) > 1


def is_correct_answer(
    user_selection: Union[str, list[str], None],
    correct_option: str,
) -> bool:
    """Return True when the user's selection exactly matches the correct answer.

    Comparison is case-insensitive and order-independent.
    Partial matches (subset or superset) are always False.
    """
    if not correct_option:
        return False
    try:
        user = normalize_selection(user_selection)
    except ValueError:
        return False
    expected = normalize_selection(correct_option)
    return user == expected
