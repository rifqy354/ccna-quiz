"""Pydantic request/response models."""
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=1)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    created_at: Optional[datetime] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class DomainSummary(BaseModel):
    domain: int
    name: str
    total_questions: int
    mastered: int
    attempted: int


class QuestionResponse(BaseModel):
    id: int
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
    option_e: Optional[str] = None
    option_f: Optional[str] = None
    option_g: Optional[str] = None
    # Hint for frontend: true when the correct answer requires multiple selections
    is_multi_answer: bool = False


class SessionStartRequest(BaseModel):
    domain: Optional[int] = Field(default=None, ge=1, le=7)
    session_type: Literal["mixed", "new", "review"] = "mixed"
    count: int = Field(default=10, ge=1, le=50)


class SessionStartResponse(BaseModel):
    session_id: int
    total_questions: int
    session_type: str


class AnswerRequest(BaseModel):
    question_id: int = Field(..., gt=0)
    # New multi-answer format: list of selected option letters
    selected_options: list[str] = Field(..., min_length=1)
    confidence: str = Field(..., pattern="^(again|hard|good|easy)$")
    response_time_ms: Optional[int] = Field(default=None, ge=0)


class AnswerResponse(BaseModel):
    is_correct: bool
    correct_option: str
    # Canonical form of what the user selected (e.g. "BDE"), for display
    user_selection: str
    explanation: str
    ocg_chapter_ref: Optional[str] = None
    ocg_section_ref: Optional[str] = None
    mastered: bool
    next_review_days: int


class SessionSummary(BaseModel):
    session_id: int
    questions_shown: int
    correct_count: int
    accuracy_pct: float
    completed_at: datetime


class DashboardStats(BaseModel):
    total_questions: int
    questions_mastered: int
    questions_attempted: int
    overall_recall_rate: float
    study_streak: int
    due_today: int
    domains: list[DomainSummary]
