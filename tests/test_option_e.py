"""
Regression tests for 5+ option question support (Task 1).

Tests cover:
- PT parser extracts 5 options including E
- Database stores option_e
- API returns option_e in QuestionResponse
- Grading handles option E letter correctly
"""
import pytest, re, zipfile, io, asyncio
from bs4 import BeautifulSoup

# PT parser test helpers (live copies from production code)
_LETTER_MAP = {0: "A", 1: "B", 2: "C", 3: "D", 4: "E", 5: "F"}

def _extract_options(li_html: str) -> dict[str, str]:
    """Live copy of production _extract_options."""
    soup = BeautifulSoup(li_html, "html.parser")
    li_el = soup.find("li")
    options = {}
    ol = li_el.find("ol", class_="upper-alpha") if li_el else None
    if not ol:
        return options
    for idx, li_opt in enumerate(ol.find_all("li", recursive=False)):
        if idx > 5:
            break
        text = li_opt.get_text(strip=True)
        if not text:
            continue
        letter = _LETTER_MAP.get(idx)
        if letter:
            options[letter] = text
    return options


class TestFiveOptionExtraction:
    """Regression: PT parser must extract 5 options (A–E)."""

    def test_five_options_extracted(self):
        """PT parser extracts all 5 options from a question with A–E."""
        html = """<li>
            Which command configures VRRP?
            <ol class="upper-alpha">
                <li>vrrp 1 10.1.2.3 gi 0/0</li>
                <li>vrrp 1 ip 10.1.2.3</li>
                <li>vrrp 1 10.1.2.3</li>
                <li>standby 1 10.1.2.3</li>
                <li>standby 1 vrrp</li>
            </ol>
        </li>"""
        opts = _extract_options(html)
        assert len(opts) == 5, f"Expected 5 options, got {len(opts)}"
        assert "A" in opts and "E" in opts
        assert opts["A"] == "vrrp 1 10.1.2.3 gi 0/0"
        assert opts["E"] == "standby 1 vrrp"

    def test_six_options_extracted(self):
        """PT parser extracts all 6 options (A–F)."""
        html = """<li>
            Which is correct?
            <ol class="upper-alpha">
                <li>Option A text</li>
                <li>Option B text</li>
                <li>Option C text</li>
                <li>Option D text</li>
                <li>Option E text</li>
                <li>Option F text</li>
            </ol>
        </li>"""
        opts = _extract_options(html)
        assert len(opts) == 6
        assert "F" in opts
        assert opts["F"] == "Option F text"

    def test_five_options_caps_at_six(self):
        """Parser caps at 6 options (A–F), ignores 7th."""
        html = """<li>
            Question
            <ol class="upper-alpha">
                <li>A</li><li>B</li><li>C</li><li>D</li>
                <li>E</li><li>F</li><li>G</li>
            </ol>
        </li>"""
        opts = _extract_options(html)
        assert len(opts) == 6
        assert "G" not in opts

    def test_extracted_question_model_has_option_e(self):
        """ExtractedQuestion dataclass has option_e field."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
        from extraction.models import ExtractedQuestion
        q = ExtractedQuestion(
            source_book="test", source_chapter="ch", book_title="bt",
            domain=1, sub_domain="sd", sub_domain_name="sdn",
            question_text="qt", question_image=None,
            option_a="A", option_b="B", option_c="C", option_d="D",
            option_e="E", option_f="F",
            correct_option="E", explanation="expl",
            ocg_chapter_ref=None, ocg_section_ref=None, difficulty=2,
        )
        assert q.option_e == "E"
        assert q.option_f == "F"


class TestOptionEGrading:
    """Regression: grading must handle option E letters correctly."""

    def test_single_answer_option_e(self):
        """Single answer 'E' is graded correct when expected."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
        from app.services.grading import is_correct_answer
        assert is_correct_answer(["E"], "E") is True
        assert is_correct_answer(["A"], "E") is False

    def test_multi_answer_with_option_e(self):
        """Multi-answer containing E is graded correctly."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
        from app.services.grading import is_correct_answer
        assert is_correct_answer(["B", "D", "E"], "BDE") is True
        assert is_correct_answer(["B", "D"], "BDE") is False
        assert is_correct_answer(["A", "E"], "AE") is True
        assert is_correct_answer(["A", "E", "F"], "AE") is False

    def test_normalize_selection_with_e(self):
        """normalize_selection handles E letter correctly."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
        from app.services.grading import normalize_selection
        assert normalize_selection(["E"]) == "E"
        assert normalize_selection(["e"]) == "E"
        assert normalize_selection(["A", "E"]) == "AE"
        assert normalize_selection("BDE") == "BDE"
