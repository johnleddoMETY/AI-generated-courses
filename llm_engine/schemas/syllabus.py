"""Syllabus schemas.

Two layers: SyllabusLLMResponse / LLMExamDomain are what the model
returns (no IDs, no timestamps); ExamDomain / Syllabus are the domain
models services hand to callers, with code-assigned slug IDs and UUIDs.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class LLMExamDomain(BaseModel):
    """One exam domain as returned by the LLM (IDs assigned later in code)."""

    name: str
    weight_percent: float
    key_topics: list[str]


class SyllabusLLMResponse(BaseModel):
    """LLM-facing syllabus payload."""

    exam_code: str | None
    domains: list[LLMExamDomain]
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
    source_note: str
    created_at: datetime
