"""Course schemas.

A Course is the fan-out product of a Roadmap: one Lesson per RoadmapItem.
The LLM produces LessonLLMResponse (content only); the course service
assigns lesson_id, item_id, and created_at in code. Lessons carry no
cross-references, so no index-remapping model is needed (unlike Roadmap).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class LessonSection(BaseModel):
    """One teaching section of a lesson."""

    heading: str
    body_markdown: str


class LessonExample(BaseModel):
    """A worked example: a scenario and its step-by-step walkthrough."""

    scenario: str
    walkthrough: str


class LessonPracticeQuestion(BaseModel):
    """An open-ended self-check question with its answer and explanation."""

    question: str
    answer: str
    explanation: str


class LessonLLMResponse(BaseModel):
    """Lesson content as returned by the LLM; IDs assigned in code."""

    title: str
    sections: list[LessonSection]
    examples: list[LessonExample]
    practice_questions: list[LessonPracticeQuestion]
    summary: str


class Lesson(BaseModel):
    """One generated lesson with code-assigned ID and its source item_id."""

    lesson_id: str
    item_id: str
    title: str
    sections: list[LessonSection]
    examples: list[LessonExample]
    practice_questions: list[LessonPracticeQuestion]
    summary: str
    created_at: datetime


class Course(BaseModel):
    """The full text course: one lesson per roadmap item, in priority order."""

    course_id: str
    roadmap_id: str
    topic: str
    certification: str
    lessons: list[Lesson]
    total_estimated_hours: float
    created_at: datetime
