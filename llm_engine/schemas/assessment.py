"""Assessment schemas.

LLM-facing models (LLMQuestion etc.) deliberately avoid list-length
constraints because OpenAI strict structured output rejects
minItems/maxItems; option count is enforced by post-validation in the
assessment service. Domain models enforce exactly 4 options.

SECURITY: Assessment carries correct_option_id and explanation per
question. Callers must strip these before exposing questions to end
users.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from llm_engine.schemas.syllabus import ExamDomain

OptionID = Literal["A", "B", "C", "D"]
Difficulty = Literal["easy", "medium", "hard"]


class LLMQuestionOption(BaseModel):
    """One answer option as returned by the LLM."""

    option_id: OptionID
    text: str


class LLMQuestion(BaseModel):
    """One MCQ as returned by the LLM (question_id assigned later in code)."""

    domain_id: str
    difficulty: Difficulty
    stem: str
    options: list[LLMQuestionOption]
    correct_option_id: OptionID
    explanation: str


class AssessmentLLMResponse(BaseModel):
    """LLM-facing assessment payload."""

    questions: list[LLMQuestion]


class QuestionOption(BaseModel):
    """One answer option."""

    option_id: OptionID
    text: str


class Question(BaseModel):
    """One MCQ with its code-assigned UUID."""

    question_id: str
    domain_id: str
    difficulty: Difficulty
    stem: str
    options: list[QuestionOption] = Field(min_length=4, max_length=4)
    correct_option_id: OptionID
    explanation: str


class Assessment(BaseModel):
    """A generated assessment, self-contained for grading.

    domains is a snapshot of the syllabus domains so grade_assessment
    needs only (assessment, answers).
    """

    assessment_id: str
    syllabus_id: str
    topic: str
    certification: str
    domains: list[ExamDomain]
    questions: list[Question]
    num_questions: int
    created_at: datetime


class UserAnswer(BaseModel):
    """A learner's answer to one question; None selected_option_id means skipped."""

    question_id: str
    selected_option_id: OptionID | None
