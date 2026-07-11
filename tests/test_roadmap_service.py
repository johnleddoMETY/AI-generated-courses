from datetime import date, datetime, timedelta, timezone

import pytest

from llm_engine.schemas import (
    DomainScore,
    ExamDomain,
    GradedAssessment,
    LLMRoadmapItem,
    LLMSkippedDomain,
    LLMStudyWeek,
    RoadmapLLMResponse,
    Syllabus,
)
from llm_engine.services.roadmap import generate_roadmap


def _syllabus() -> Syllabus:
    return Syllabus(
        syllabus_id="syllabus-1",
        topic="Cloud Architecture",
        certification="AWS SAA-C03",
        exam_code="SAA-C03",
        domains=[
            ExamDomain(domain_id="domain-a", name="Domain A", weight_percent=60.0, key_topics=["a"]),
            ExamDomain(domain_id="domain-b", name="Domain B", weight_percent=40.0, key_topics=["b"]),
        ],
        source_note="Test syllabus.",
        created_at=datetime(2026, 7, 11, tzinfo=timezone.utc),
    )


def _graded() -> GradedAssessment:
    return GradedAssessment(
        assessment_id="assessment-1",
        overall_score_percent=30.0,
        question_results=[],
        domain_scores=[
            DomainScore(
                domain_id="domain-a",
                domain_name="Domain A",
                weight_percent=60.0,
                questions_total=2,
                questions_correct=1,
                score_percent=50.0,
                proficiency="developing",
            ),
            DomainScore(
                domain_id="domain-b",
                domain_name="Domain B",
                weight_percent=40.0,
                questions_total=1,
                questions_correct=1,
                score_percent=100.0,
                proficiency="proficient",
            ),
        ],
        gaps=[],
        diagnostic_summary="One developing domain.",
        strengths_summary="Domain B proficient.",
        graded_at=datetime(2026, 7, 11, tzinfo=timezone.utc),
    )


def _llm_response(weekly: bool) -> RoadmapLLMResponse:
    return RoadmapLLMResponse(
        items=[
            LLMRoadmapItem(
                domain_id="domain-a",
                title="Core Domain A concepts",
                objective="Fix the 50% score.",
                subtopics=["a1", "a2"],
                why_included="Scored 50% (developing) in the highest-weight domain.",
                estimated_hours=4.0,
                prerequisite_indices=[],
            ),
            LLMRoadmapItem(
                domain_id="domain-a",
                title="Advanced Domain A",
                objective="Build on the core concepts.",
                subtopics=["a3"],
                why_included="Follows from the demonstrated core gap.",
                estimated_hours=2.5,
                prerequisite_indices=[0, 99],  # 99 is invalid -> dropped
            ),
        ],
        skipped_domains=[
            LLMSkippedDomain(domain_id="domain-b", reason="Proficient (100%); skipped."),
        ],
        weekly_plan=(
            [
                LLMStudyWeek(week_number=1, focus="Core", item_indices=[0], estimated_hours=4.0),
                LLMStudyWeek(week_number=2, focus="Review", item_indices=[1], estimated_hours=2.5),
            ]
            if weekly
            else None
        ),
        guidance_summary="Focus on Domain A only.",
    )


def test_roadmap_assembles_ids_priorities_and_prereqs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "llm_engine.services.roadmap.structured_completion",
        lambda *args, **kwargs: _llm_response(weekly=False),
    )

    roadmap = generate_roadmap(_syllabus(), _graded())

    assert len(roadmap.roadmap_id) == 36
    assert roadmap.assessment_id == "assessment-1"
    assert roadmap.exam_date is None
    assert roadmap.weekly_plan is None
    assert [item.priority for item in roadmap.items] == [1, 2]
    assert all(len(item.item_id) == 36 for item in roadmap.items)
    assert roadmap.items[1].prerequisites == [roadmap.items[0].item_id]  # invalid 99 dropped
    assert roadmap.total_estimated_hours == 6.5
    assert roadmap.skipped_domains[0].domain_id == "domain-b"


def test_roadmap_with_exam_date_maps_weekly_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def fake_structured_completion(*args: object, **kwargs: object) -> RoadmapLLMResponse:
        captured["user_prompt"] = args[2] if len(args) > 2 else kwargs["user_prompt"]
        return _llm_response(weekly=True)

    monkeypatch.setattr(
        "llm_engine.services.roadmap.structured_completion", fake_structured_completion
    )

    exam_date = date.today() + timedelta(days=28)
    roadmap = generate_roadmap(_syllabus(), _graded(), exam_date=exam_date)

    assert roadmap.exam_date == exam_date
    assert roadmap.weekly_plan is not None
    assert roadmap.weekly_plan[0].item_ids == [roadmap.items[0].item_id]
    assert "weeks remain" in captured["user_prompt"]  # weeks computed in Python, passed in
