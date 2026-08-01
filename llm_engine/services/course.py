"""Course generation: fan out each RoadmapItem into one text lesson."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import uuid4

from llm_engine.client import structured_completion
from llm_engine.prompts.course_prompts import LESSON_SYSTEM_V1, build_lesson_user_prompt
from llm_engine.schemas import (
    Course,
    Lesson,
    LessonLLMResponse,
    Roadmap,
    RoadmapItem,
)

logger = logging.getLogger(__name__)


def generate_lesson(item: RoadmapItem, topic: str, certification: str) -> Lesson:
    """Generate one text lesson for a single roadmap item (one LLM call).

    The lesson_id, item_id, and created_at are assigned in code; the LLM
    returns content only.
    """
    llm_response = structured_completion(
        LessonLLMResponse,
        LESSON_SYSTEM_V1,
        build_lesson_user_prompt(
            item_block=_format_item_block(item),
            topic=topic,
            certification=certification,
        ),
        task="lesson",
    )

    return Lesson(
        lesson_id=str(uuid4()),
        item_id=item.item_id,
        title=llm_response.title,
        sections=llm_response.sections,
        examples=llm_response.examples,
        practice_questions=llm_response.practice_questions,
        summary=llm_response.summary,
        created_at=datetime.now(timezone.utc),
    )


def generate_course(roadmap: Roadmap) -> Course:
    """Generate a full text course by fanning out over the roadmap's items.

    One lesson is generated per RoadmapItem, via a thread pool (each lesson
    is an independent LLM call, so this is a latency win, not a CPU one).
    Results are returned in roadmap.items order (priority order) regardless
    of completion order. Fail-fast: if any lesson generation raises, the
    exception propagates and no partial course is returned — other lessons
    already in flight are not cancelled. Progress is logged per lesson so a
    slow or failed fan-out can be located — the raised error itself does not
    identify which item failed.
    """
    total = len(roadmap.items)

    def _generate(indexed_item: tuple[int, RoadmapItem]) -> Lesson:
        position, item = indexed_item
        logger.info("Generating lesson %d/%d: %s", position, total, item.title)
        return generate_lesson(item, roadmap.topic, roadmap.certification)

    with ThreadPoolExecutor(max_workers=total or 1) as executor:
        lessons = list(executor.map(_generate, enumerate(roadmap.items, start=1)))

    return Course(
        course_id=str(uuid4()),
        roadmap_id=roadmap.roadmap_id,
        topic=roadmap.topic,
        certification=roadmap.certification,
        lessons=lessons,
        total_estimated_hours=round(sum(item.estimated_hours for item in roadmap.items), 1),
        created_at=datetime.now(timezone.utc),
    )


def _format_item_block(item: RoadmapItem) -> str:
    lines = [
        f"Title: {item.title}",
        f"Domain: {item.domain_id}",
        f"Objective: {item.objective}",
        f"Subtopics: {', '.join(item.subtopics)}",
        f"Estimated hours: {item.estimated_hours}",
        f"Why this was assigned to the learner: {item.why_included}",
    ]
    return "\n".join(lines)
