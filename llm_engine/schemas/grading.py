"""Grading schemas.

GradingDiagnosis is LLM-facing: qualitative diagnosis plus, for
fill_in_blank/full_text questions only, the numeric judgment those types
require (Python cannot grade free text deterministically). Scoring for
single_answer/multi_answer is deterministic Python; DomainScore's
score_percent averages per-question score_percent across all types.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from llm_engine.schemas.assessment import OptionID
from llm_engine.schemas.syllabus import QuestionType

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


class FreeTextJudgment(BaseModel):
    """LLM's numeric judgment of one fill_in_blank/full_text answer.

    fill_in_blank judgments are treated as binary by the service (>=50
    rounds to 100, otherwise 0); full_text judgments are used as-is,
    0-100.
    """

    question_id: str
    score_percent: float
    rationale: str


class GradingDiagnosis(BaseModel):
    """LLM-facing diagnosis: gaps, narrative, and free-text judgments."""

    gaps: list[KnowledgeGap]
    per_domain_notes: list[DomainQualitativeNote]
    free_text_judgments: list[FreeTextJudgment]
    diagnostic_summary: str
    strengths_summary: str


class QuestionResult(BaseModel):
    """Per-question grading outcome.

    Exactly the fields matching question_type are populated:
    selected_option_id/correct_option_id (single_answer),
    selected_option_ids/correct_option_ids (multi_answer), or text_answer
    (fill_in_blank/full_text). score_percent is 0 or 100 for
    single_answer/multi_answer/fill_in_blank (all-or-nothing) and 0-100
    for full_text (partial credit). correct is score_percent == 100.
    """

    question_id: str
    domain_id: str
    question_type: QuestionType
    correct: bool
    score_percent: float
    selected_option_id: OptionID | None = None
    correct_option_id: OptionID | None = None
    selected_option_ids: list[OptionID] | None = None
    correct_option_ids: list[OptionID] | None = None
    text_answer: str | None = None
    explanation: str


class DomainScore(BaseModel):
    """Per-domain score: mean of question score_percent, threshold-derived proficiency."""

    domain_id: str
    domain_name: str
    weight_percent: float
    questions_total: int
    questions_correct: float
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
