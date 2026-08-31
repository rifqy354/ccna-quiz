"""Parser for Practice Tests EPUB."""
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from bs4 import BeautifulSoup

from .models import ExtractedQuestion

CHAPTER_DOMAIN_MAP = {
    "c01": (1, "ch01"),
    "c02": (2, "ch02"),
    "c03": (3, "ch03"),
    "c04": (4, "ch04"),
    "c05": (5, "ch05"),
    "c06": (6, "ch06"),
    "c07": (None, "ch07"),
    "c08": (None, "ch08"),
}


def _extract_epub(epub_path: str) -> Path:
    tmp = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(epub_path, "r") as z:
        z.extractall(tmp)
    return tmp


def _parse_answer_key(answer_key_path: Path) -> dict[int, tuple[str, str]]:
    """Parse b01.xhtml answer key: question_num -> (correct_letter, explanation)."""
    if not answer_key_path.exists():
        return {}
    soup = BeautifulSoup(answer_key_path.read_text(encoding="utf-8"), "lxml")
    answers = {}
    text = soup.get_text()

    # Match patterns like: "1. A\nExplanation..."
    pattern = re.compile(r"(\d+)\.\s+([A-D])\s*\n(.*?)(?=\n\d+\.|\Z)", re.DOTALL)
    for m in pattern.finditer(text):
        num = int(m.group(1))
        letter = m.group(2).strip()
        explanation = m.group(3).strip()
        answers[num] = (letter, explanation)

    return answers


def _parse_questions_in_chapter(
    chapter_path: Path,
    chapter_key: str,
    domain: int | None,
    book_title: str,
    answer_key: dict[int, tuple[str, str]],
    images_dir: str,
) -> list[ExtractedQuestion]:
    """Extract questions from a chapter XHTML file."""
    if not chapter_path.exists():
        return []

    soup = BeautifulSoup(chapter_path.read_text(encoding="utf-8"), "lxml")
    questions = []
    question_num = 0

    for elem in soup.find_all(["p", "div"]):
        text = elem.get_text(strip=True)
        # Detect numbered questions: "1. ", "2. ", etc.
        m = re.match(r"^(\d+)\.\s+(.*)", text, re.DOTALL)
        if not m:
            continue

        question_num = int(m.group(1))
        question_text = m.group(2).strip()

        # Extract the question block (this element + following siblings until next question)
        block_text = elem.get_text(separator=" ", strip=True)

        # Find 4 options A/B/C/D
        opt_a = opt_b = opt_c = opt_d = ""
        a_m = re.search(r"(?:^|[,\n])\s*[Aa]\.\s*([^\n]+?)(?=\s*[Bb]\.\s|\s*[Cc]\.\s|\s*[Dd]\.\s|$)", block_text)
        b_m = re.search(r"[Bb]\.\s*([^\n]+?)(?=\s*[Cc]\.\s|\s*[Dd]\.\s|$)", block_text)
        c_m = re.search(r"[Cc]\.\s*([^\n]+?)(?=\s*[Dd]\.\s|$)", block_text)
        d_m = re.search(r"[Dd]\.\s*([^\n]+)", block_text)

        if a_m:
            opt_a = a_m.group(1).strip()
        if b_m:
            opt_b = b_m.group(1).strip()
        if c_m:
            opt_c = c_m.group(1).strip()
        if d_m:
            opt_d = d_m.group(1).strip()

        if not (opt_a and opt_b and opt_c and opt_d):
            continue

        # Handle image
        img_tag = elem.find("img")
        img_filename = None
        if img_tag and img_tag.get("src"):
            src = img_tag["src"]
            img_filename = f"{chapter_key}_q{question_num}_{Path(src).name}"
            # Copy image to images_dir
            img_src_path = chapter_path.parent / src
            if img_src_path.exists():
                shutil.copy(img_src_path, os.path.join(images_dir, img_filename))

        correct, explanation = answer_key.get(question_num, ("A", ""))

        questions.append(ExtractedQuestion(
            source_book="practice_tests",
            source_chapter=chapter_key,
            book_title=book_title,
            domain=domain,
            sub_domain=None,
            sub_domain_name=None,
            question_text=question_text[:1000],
            question_image=img_filename,
            option_a=opt_a[:500],
            option_b=opt_b[:500],
            option_c=opt_c[:500],
            option_d=opt_d[:500],
            correct_option=correct,
            explanation=explanation[:2000],
            ocg_chapter_ref=None,
            ocg_section_ref=None,
            difficulty=2,
        ))

    return questions


def parse_practice_tests_epub(epub_path: str, images_dir: str) -> list[ExtractedQuestion]:
    """Parse Practice Tests EPUB and return all questions."""
    tmp = _extract_epub(epub_path)

    # Find answer key
    answer_key_path = None
    for root, _, files in os.walk(tmp):
        for f in files:
            if f.startswith("b01"):
                answer_key_path = Path(root) / f
                break
    answer_key = _parse_answer_key(answer_key_path) if answer_key_path else {}

    all_questions = []

    for chapter_key, (domain, ch_num) in CHAPTER_DOMAIN_MAP.items():
        book_title = f"Practice Tests - Chapter {ch_num.lstrip('ch')}"

        # Find chapter file
        chapter_file = None
        for ext in ["xhtml", "html", "htm"]:
            candidate = tmp / f"chapter_{chapter_key}.{ext}"
            if candidate.exists():
                chapter_file = candidate
                break
            # Also try e.g. c01.xhtml
            candidate2 = tmp / f"{chapter_key}.{ext}"
            if candidate2.exists():
                chapter_file = candidate2
                break

        if not chapter_file:
            # Try case-insensitive search
            for f in tmp.rglob(f"*{chapter_key}*"):
                if f.suffix in (".xhtml", ".html", ".htm"):
                    chapter_file = f
                    break

        if chapter_file:
            qs = _parse_questions_in_chapter(
                chapter_file, ch_num, domain, book_title, answer_key, images_dir
            )
            all_questions.extend(qs)
            print(f"  {chapter_key}: {len(qs)} questions")

    return all_questions
