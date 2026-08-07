"""Syllabus schemas.

Two layers: SyllabusLLMResponse / LLMExamDomain are what the model
returns (no IDs, no timestamps); ExamDomain / Syllabus are the domain
models services hand to callers, with code-assigned slug IDs and UUIDs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

QuestionType = Literal["single_answer", "multi_answer", "fill_in_blank", "full_text"]


class QuestionTypeWeight(BaseModel):
    """One question-type's share of the exam, e.g. 80% single-answer, 20% multi-answer."""

    question_type: QuestionType
    weight_percent: float


class LLMExamDomain(BaseModel):
    """One exam domain as returned by the LLM (IDs assigned later in code)."""

    name: str
    weight_percent: float
    key_topics: list[str]


class SyllabusLLMResponse(BaseModel):
    """LLM-facing syllabus payload."""

    exam_code: str | None
    domains: list[LLMExamDomain]
    question_type_mix: list[QuestionTypeWeight]
    source_note: str


class ExamDomain(BaseModel):
    """One exam domain with its code-assigned slug ID."""

    domain_id: str
    name: str
    weight_percent: float
    key_topics: list[str]


class Syllabus(BaseModel):
    """A certification exam blueprint; the anchor artifact of the pipeline."""

    syllabus_id: str
    topic: str
    certification: str
    exam_code: str | None
    domains: list[ExamDomain]
    question_type_mix: list[QuestionTypeWeight]
    source_note: str
    created_at: datetime
