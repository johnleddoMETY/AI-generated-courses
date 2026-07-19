from datetime import datetime, timezone

import pytest

from llm_engine.exceptions import LLMCallError
from llm_engine.schemas import (
    LessonExample,
    LessonLLMResponse,
    LessonPracticeQuestion,
    LessonSection,
    Roadmap,
    RoadmapItem,
)
from llm_engine.services.course import generate_course, generate_lesson

_NOW = datetime(2026, 7, 11, tzinfo=timezone.utc)


def _item(item_id: str, domain: str, hours: float) -> RoadmapItem:
    return RoadmapItem(
        item_id=item_id,
        domain_id=domain,
        title=f"Lesson for {domain}",
        objective="Close the gap.",
        subtopics=["a", "b"],
        why_included="Scored low here.",
        priority=1,
        estimated_hours=hours,
        prerequisites=[],
    )


def _roadmap(items: list[RoadmapItem]) -> Roadmap:
    return Roadmap(
        roadmap_id="roadmap-1",
        assessment_id="assessment-1",
        syllabus_id="syllabus-1",
        topic="Cloud Architecture",
        certification="AWS SAA-C03",
        exam_date=None,
        items=items,
        skipped_domains=[],
        total_estimated_hours=sum(i.estimated_hours for i in items),
        weekly_plan=None,
        guidance_summary="Focus on gaps.",
        created_at=_NOW,
    )


def _llm_lesson(title: str) -> LessonLLMResponse:
    return LessonLLMResponse(
        title=title,
        sections=[LessonSection(heading="Intro", body_markdown="Body.")],
        examples=[LessonExample(scenario="Scenario", walkthrough="Walk.")],
        practice_questions=[
            LessonPracticeQuestion(question="Q?", answer="A.", explanation="Because.")
        ],
        summary="Summary.",
    )


def test_generate_lesson_assigns_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "llm_engine.services.course.structured_completion",
        lambda *args, **kwargs: _llm_lesson("IAM basics"),
    )
    item = _item("item-1", "domain-a", 4.0)

    lesson = generate_lesson(item, "Cloud Architecture", "AWS SAA-C03")

    assert lesson.item_id == "item-1"
    assert len(lesson.lesson_id) == 36
    assert lesson.title == "IAM basics"
    assert lesson.sections[0].heading == "Intro"
    assert lesson.created_at.tzinfo is not None


def test_generate_course_fans_out_over_items(monkeypatch: pytest.MonkeyPatch) -> None:
    titles = iter(["Lesson A", "Lesson B"])
    monkeypatch.setattr(
        "llm_engine.services.course.structured_completion",
        lambda *args, **kwargs: _llm_lesson(next(titles)),
    )
    roadmap = _roadmap([_item("item-1", "domain-a", 4.0), _item("item-2", "domain-b", 2.5)])

    course = generate_course(roadmap)

    assert len(course.lessons) == 2
    assert [lesson.item_id for lesson in course.lessons] == ["item-1", "item-2"]
    assert [lesson.title for lesson in course.lessons] == ["Lesson A", "Lesson B"]
    assert len(course.course_id) == 36
    assert course.roadmap_id == "roadmap-1"
    assert course.topic == "Cloud Architecture"
    assert course.certification == "AWS SAA-C03"
    assert course.total_estimated_hours == 6.5


def test_generate_course_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def flaky(*args: object, **kwargs: object) -> LessonLLMResponse:
        calls["n"] += 1
        if calls["n"] == 2:
            raise LLMCallError("provider exploded")
        return _llm_lesson("ok")

    monkeypatch.setattr("llm_engine.services.course.structured_completion", flaky)
    roadmap = _roadmap([_item("item-1", "domain-a", 4.0), _item("item-2", "domain-b", 2.5)])

    with pytest.raises(LLMCallError):
        generate_course(roadmap)


def test_generate_course_logs_progress_per_lesson(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(
        "llm_engine.services.course.structured_completion",
        lambda *args, **kwargs: _llm_lesson("ok"),
    )
    roadmap = _roadmap([_item("item-1", "domain-a", 4.0), _item("item-2", "domain-b", 2.5)])

    with caplog.at_level("INFO", logger="llm_engine.services.course"):
        generate_course(roadmap)

    messages = [record.getMessage() for record in caplog.records]
    assert "Generating lesson 1/2: Lesson for domain-a" in messages
    assert "Generating lesson 2/2: Lesson for domain-b" in messages
