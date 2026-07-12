"""Roadmap schemas.

LLM-facing models reference items by 0-based index (the LLM never
generates IDs); the roadmap service maps indices to code-generated
UUID item_ids and assigns priority from list order.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class LLMRoadmapItem(BaseModel):
    """One study item as returned by the LLM.

    prerequisite_indices are 0-based positions into the same items list.
    """

    domain_id: str
    title: str
    objective: str
    subtopics: list[str]
    why_included: str
    estimated_hours: float
    prerequisite_indices: list[int]


class LLMStudyWeek(BaseModel):
    """One study week as returned by the LLM; item_indices are 0-based."""

    week_number: int
    focus: str
    item_indices: list[int]
    estimated_hours: float


class LLMSkippedDomain(BaseModel):
    """A domain the roadmap deliberately skips or compresses, with the reason."""

    domain_id: str
    reason: str


class RoadmapLLMResponse(BaseModel):
    """LLM-facing roadmap payload; items ordered most-important first."""

    items: list[LLMRoadmapItem]
    skipped_domains: list[LLMSkippedDomain]
    weekly_plan: list[LLMStudyWeek] | None
    guidance_summary: str


class RoadmapItem(BaseModel):
    """One study item with code-assigned UUID and priority (1 = first)."""

    item_id: str
    domain_id: str
    title: str
    objective: str
    subtopics: list[str]
    why_included: str
    priority: int
    estimated_hours: float
    prerequisites: list[str]


class StudyWeek(BaseModel):
    """One week of the study plan, referencing items by item_id."""

    week_number: int
    focus: str
    item_ids: list[str]
    estimated_hours: float


class SkippedDomain(BaseModel):
    """A skipped/compressed domain with its rationale."""

    domain_id: str
    reason: str


class Roadmap(BaseModel):
    """The personalized study roadmap; teaches only what the learner lacks."""

    roadmap_id: str
    assessment_id: str
    syllabus_id: str
    topic: str
    certification: str
    exam_date: date | None
    items: list[RoadmapItem]
    skipped_domains: list[SkippedDomain]
    total_estimated_hours: float
    weekly_plan: list[StudyWeek] | None
    guidance_summary: str
    created_at: datetime
