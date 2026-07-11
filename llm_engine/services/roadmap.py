"""Roadmap generation: one LLM call turning graded results into a gap-targeted plan."""

from __future__ import annotations

import logging
import math
from datetime import date, datetime, timezone
from uuid import uuid4

from llm_engine.client import structured_completion
from llm_engine.prompts.roadmap_prompts import ROADMAP_SYSTEM_V1, build_roadmap_user_prompt
from llm_engine.schemas import (
    GradedAssessment,
    Roadmap,
    RoadmapItem,
    RoadmapLLMResponse,
    SkippedDomain,
    StudyWeek,
    Syllabus,
)

logger = logging.getLogger(__name__)


def generate_roadmap(
    syllabus: Syllabus,
    graded: GradedAssessment,
    exam_date: date | None = None,
) -> Roadmap:
    """Generate a study roadmap that teaches only what the learner doesn't know.

    Weeks-remaining is computed here when exam_date is given (the LLM never
    does date math). Item UUIDs and priorities are assigned in code from the
    LLM's ordered list; prerequisite/week item indices are mapped to the
    generated item_ids, dropping out-of-range or self-referencing indices.
    """
    weeks_remaining: int | None = None
    if exam_date is not None:
        weeks_remaining = max(1, math.ceil((exam_date - date.today()).days / 7))

    llm_response = structured_completion(
        RoadmapLLMResponse,
        ROADMAP_SYSTEM_V1,
        build_roadmap_user_prompt(
            syllabus_block=_format_syllabus_block(syllabus),
            results_block=_format_results_block(graded),
            schedule_block=_format_schedule_block(exam_date, weeks_remaining),
        ),
        task="roadmap",
    )

    item_ids = [str(uuid4()) for _ in llm_response.items]
    items = [
        RoadmapItem(
            item_id=item_ids[index],
            domain_id=llm_item.domain_id,
            title=llm_item.title,
            objective=llm_item.objective,
            subtopics=llm_item.subtopics,
            why_included=llm_item.why_included,
            priority=index + 1,
            estimated_hours=llm_item.estimated_hours,
            prerequisites=_map_indices(llm_item.prerequisite_indices, item_ids, exclude=index),
        )
        for index, llm_item in enumerate(llm_response.items)
    ]

    weekly_plan: list[StudyWeek] | None = None
    if exam_date is not None and llm_response.weekly_plan:
        weekly_plan = [
            StudyWeek(
                week_number=week.week_number,
                focus=week.focus,
                item_ids=_map_indices(week.item_indices, item_ids),
                estimated_hours=week.estimated_hours,
            )
            for week in llm_response.weekly_plan
        ]

    return Roadmap(
        roadmap_id=str(uuid4()),
        assessment_id=graded.assessment_id,
        syllabus_id=syllabus.syllabus_id,
        topic=syllabus.topic,
        certification=syllabus.certification,
        exam_date=exam_date,
        items=items,
        skipped_domains=[
            SkippedDomain(domain_id=skipped.domain_id, reason=skipped.reason)
            for skipped in llm_response.skipped_domains
        ],
        total_estimated_hours=round(sum(item.estimated_hours for item in items), 1),
        weekly_plan=weekly_plan,
        guidance_summary=llm_response.guidance_summary,
        created_at=datetime.now(timezone.utc),
    )


def _map_indices(indices: list[int], item_ids: list[str], exclude: int | None = None) -> list[str]:
    """Map LLM 0-based item indices to generated item_ids, dropping invalid ones."""
    valid: list[str] = []
    for index in indices:
        if 0 <= index < len(item_ids) and index != exclude:
            valid.append(item_ids[index])
        else:
            logger.warning("Dropping invalid roadmap item index %d", index)
    return valid


def _format_syllabus_block(syllabus: Syllabus) -> str:
    lines = [f"Topic: {syllabus.topic}", f"Certification: {syllabus.certification}", "Domains:"]
    lines += [
        f"- {domain.domain_id}: {domain.name} ({domain.weight_percent:.0f}% of exam) — "
        f"key topics: {', '.join(domain.key_topics)}"
        for domain in syllabus.domains
    ]
    return "\n".join(lines)


def _format_results_block(graded: GradedAssessment) -> str:
    lines = [f"Overall weighted score: {graded.overall_score_percent}%", "Per-domain scores:"]
    lines += [
        f"- {score.domain_id} ({score.domain_name}, {score.weight_percent:.0f}% of exam): "
        f"{score.score_percent}% ({score.questions_correct}/{score.questions_total}) "
        f"-> {score.proficiency}"
        for score in graded.domain_scores
    ]
    if graded.gaps:
        lines.append("Identified gaps:")
        lines += [
            f"- [{gap.severity}] {gap.domain_id}: {gap.gap_summary} "
            f"(evidence: {', '.join(gap.evidence_question_ids) or 'none'})"
            for gap in graded.gaps
        ]
    lines.append(f"Diagnostic summary: {graded.diagnostic_summary}")
    lines.append(f"Strengths: {graded.strengths_summary}")
    return "\n".join(lines)


def _format_schedule_block(exam_date: date | None, weeks_remaining: int | None) -> str:
    if exam_date is None:
        return "No exam date provided. Set weekly_plan to null."
    return (
        f"Exam date: {exam_date.isoformat()}. {weeks_remaining} weeks remain from today. "
        f"A weekly plan is required: at most {weeks_remaining} weeks, ending with a "
        f"final review week."
    )
