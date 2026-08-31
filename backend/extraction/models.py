"""Models for extraction pipeline."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExtractedQuestion:
    source_book: str
    source_chapter: str
    book_title: str
    domain: Optional[int]
    sub_domain: Optional[str]
    sub_domain_name: Optional[str]
    question_text: str
    question_image: Optional[str]
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: str
    explanation: str
    ocg_chapter_ref: Optional[str]
    ocg_section_ref: Optional[str]
    difficulty: int = 2
