"""Grading schemas.

GradingDiagnosis is LLM-facing: purely qualitative, no numeric scores —
scoring is deterministic Python. GradedAssessment is assembled in code
from computed scores plus the diagnosis.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from llm_engine.schemas.assessment import OptionID

Severity = Literal["minor", "moderate", "critical"]
Proficiency = Literal["weak", "developing", "proficient"]


class KnowledgeGap(BaseModel):
    """A concept-level gap, backed by question-ID evidence."""

    domain_id: str
    gap_summary: str
    severity: Severity
    evidence_question_ids: list[str]


class DomainQualitativeNote(BaseModel):
    """One qualitative note about the learner's performance in a domain."""

    domain_id: str
    note: str


class GradingDiagnosis(BaseModel):
    """LLM-facing diagnosis: gaps and narrative only, never numbers."""

    gaps: list[KnowledgeGap]
    per_domain_notes: list[DomainQualitativeNote]
    diagnostic_summary: str
    strengths_summary: str


class QuestionResult(BaseModel):
    """Deterministic per-question grading outcome."""

    question_id: str
    domain_id: str
    correct: bool
    selected_option_id: OptionID | None
    correct_option_id: OptionID
    explanation: str


class DomainScore(BaseModel):
    """Deterministic per-domain score with a threshold-derived proficiency label."""

    domain_id: str
    domain_name: str
    weight_percent: float
    questions_total: int
    questions_correct: int
    score_percent: float
    proficiency: Proficiency


class GradedAssessment(BaseModel):
    """Full grading result: Python-computed scores + LLM qualitative diagnosis."""

    assessment_id: str
    overall_score_percent: float
    question_results: list[QuestionResult]
    domain_scores: list[DomainScore]
    gaps: list[KnowledgeGap]
    diagnostic_summary: str
    strengths_summary: str
    graded_at: datetime
