"""Assessment schemas.

LLM-facing models deliberately avoid list-length constraints because
OpenAI strict structured output rejects minItems/maxItems; option count
is enforced by post-validation in the assessment service. Domain models
enforce exactly 4 options for the MCQ question types.

Each question type (single_answer, multi_answer, fill_in_blank,
full_text) is its own model, tagged by question_type and joined into a
discriminated union — Question/LLMQuestion are type aliases, not
classes, so they cannot be called as constructors; build the specific
per-type model instead.

SECURITY: MCQ questions carry correct_option_id/correct_option_ids;
fill_in_blank carries accepted_answers; full_text carries rubric.
explanation is present on all types. Callers must strip these
answer-revealing fields before exposing questions to end users.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from llm_engine.schemas.syllabus import ExamDomain

OptionID = Literal["A", "B", "C", "D"]
Difficulty = Literal["easy", "medium", "hard"]


class LLMQuestionOption(BaseModel):
    """One answer option as returned by the LLM."""

    option_id: OptionID
    text: str


class SingleAnswerLLMQuestion(BaseModel):
    """One single-correct-answer MCQ as returned by the LLM."""

    question_type: Literal["single_answer"] = "single_answer"
    domain_id: str
    difficulty: Difficulty
    stem: str
    options: list[LLMQuestionOption]
    correct_option_id: OptionID
    explanation: str


class MultiAnswerLLMQuestion(BaseModel):
    """One "select all that apply" MCQ as returned by the LLM."""

    question_type: Literal["multi_answer"] = "multi_answer"
    domain_id: str
    difficulty: Difficulty
    stem: str
    options: list[LLMQuestionOption]
    correct_option_ids: list[OptionID]
    explanation: str


class FillInBlankLLMQuestion(BaseModel):
    """One fill-in-the-blank question as returned by the LLM."""

    question_type: Literal["fill_in_blank"] = "fill_in_blank"
    domain_id: str
    difficulty: Difficulty
    stem: str
    accepted_answers: list[str]
    explanation: str


class FullTextLLMQuestion(BaseModel):
    """One free-text/essay question as returned by the LLM."""

    question_type: Literal["full_text"] = "full_text"
    domain_id: str
    difficulty: Difficulty
    stem: str
    rubric: str
    explanation: str


LLMQuestion = Annotated[
    SingleAnswerLLMQuestion | MultiAnswerLLMQuestion | FillInBlankLLMQuestion | FullTextLLMQuestion,
    Field(discriminator="question_type"),
]


class AssessmentLLMResponse(BaseModel):
    """LLM-facing assessment payload."""

    questions: list[LLMQuestion]


class QuestionOption(BaseModel):
    """One answer option."""

    option_id: OptionID
    text: str


class SingleAnswerQuestion(BaseModel):
    """One single-correct-answer MCQ with its code-assigned UUID."""

    question_type: Literal["single_answer"] = "single_answer"
    question_id: str
    domain_id: str
    difficulty: Difficulty
    stem: str
    options: list[QuestionOption] = Field(min_length=4, max_length=4)
    correct_option_id: OptionID
    explanation: str


class MultiAnswerQuestion(BaseModel):
    """One "select all that apply" MCQ with its code-assigned UUID."""

    question_type: Literal["multi_answer"] = "multi_answer"
    question_id: str
    domain_id: str
    difficulty: Difficulty
    stem: str
    options: list[QuestionOption] = Field(min_length=4, max_length=4)
    correct_option_ids: list[OptionID]
    explanation: str


class FillInBlankQuestion(BaseModel):
    """One fill-in-the-blank question with its code-assigned UUID."""

    question_type: Literal["fill_in_blank"] = "fill_in_blank"
    question_id: str
    domain_id: str
    difficulty: Difficulty
    stem: str
    accepted_answers: list[str]
    explanation: str


class FullTextQuestion(BaseModel):
    """One free-text/essay question with its code-assigned UUID."""

    question_type: Literal["full_text"] = "full_text"
    question_id: str
    domain_id: str
    difficulty: Difficulty
    stem: str
    rubric: str
    explanation: str


Question = Annotated[
    SingleAnswerQuestion | MultiAnswerQuestion | FillInBlankQuestion | FullTextQuestion,
    Field(discriminator="question_type"),
]


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
    """A learner's answer to one question.

    Exactly one type-specific field is populated, matching the question's
    question_type: selected_option_id (single_answer), selected_option_ids
    (multi_answer), or text_answer (fill_in_blank / full_text). All-None
    means skipped.
    """

    question_id: str
    selected_option_id: OptionID | None = None
    selected_option_ids: list[OptionID] | None = None
    text_answer: str | None = None
