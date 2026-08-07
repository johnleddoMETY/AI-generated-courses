from datetime import datetime, timezone

import pytest

from llm_engine.schemas import (
    Assessment,
    Course,
    ExamDomain,
    GradedAssessment,
    Lesson,
    QuestionTypeWeight,
    Roadmap,
    RoadmapItem,
    Syllabus,
)
from llm_engine.services.pipeline import run_full_pipeline


def _syllabus() -> Syllabus:
    return Syllabus(
        syllabus_id="syllabus-1",
        topic="Test Topic",
        certification="Test Cert",
        exam_code="TEST-001",
        domains=[],
        question_type_mix=[QuestionTypeWeight(question_type="single_answer", weight_percent=100.0)],
        source_note="Test",
        created_at=datetime(2026, 7, 11, tzinfo=timezone.utc),
    )


def _assessment() -> Assessment:
    return Assessment(
        assessment_id="assessment-1",
        syllabus_id="syllabus-1",
        topic="Test Topic",
        certification="Test Cert",
        domains=[],
        questions=[],
        num_questions=0,
        created_at=datetime(2026, 7, 11, tzinfo=timezone.utc),
    )


def _graded_assessment() -> GradedAssessment:
    return GradedAssessment(
        assessment_id="assessment-1",
        overall_score_percent=50.0,
        question_results=[],
        domain_scores=[],
        gaps=[],
        diagnostic_summary="Test",
        strengths_summary="Test",
        graded_at=datetime(2026, 7, 11, tzinfo=timezone.utc),
    )


def _roadmap() -> Roadmap:
    return Roadmap(
        roadmap_id="roadmap-1",
        assessment_id="assessment-1",
        syllabus_id="syllabus-1",
        topic="Test Topic",
        certification="Test Cert",
        items=[],
        skipped_domains=[],
        total_estimated_hours=0.0,
        exam_date=None,
        weekly_plan=None,
        guidance_summary="Test",
        created_at=datetime(2026, 7, 11, tzinfo=timezone.utc),
    )


def _course() -> Course:
    return Course(
        course_id="course-1",
        roadmap_id="roadmap-1",
        topic="Test Topic",
        certification="Test Cert",
        lessons=[],
        total_estimated_hours=0.0,
        created_at=datetime(2026, 7, 11, tzinfo=timezone.utc),
    )


def test_run_full_pipeline_returns_five_tuple(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that run_full_pipeline returns a 5-tuple with correct types."""
    monkeypatch.setattr(
        "llm_engine.services.pipeline.generate_syllabus",
        lambda *args, **kwargs: _syllabus(),
    )
    monkeypatch.setattr(
        "llm_engine.services.pipeline.generate_assessment",
        lambda *args, **kwargs: _assessment(),
    )
    monkeypatch.setattr(
        "llm_engine.services.pipeline.grade_assessment",
        lambda *args, **kwargs: _graded_assessment(),
    )
    monkeypatch.setattr(
        "llm_engine.services.pipeline.generate_roadmap",
        lambda *args, **kwargs: _roadmap(),
    )
    monkeypatch.setattr(
        "llm_engine.services.pipeline.generate_course",
        lambda *args, **kwargs: _course(),
    )

    result = run_full_pipeline(
        topic="Test Topic",
        certification="Test Cert",
        answer_provider=lambda _: [],
    )

    assert isinstance(result, tuple)
    assert len(result) == 5
    assert isinstance(result[0], Syllabus)
    assert isinstance(result[1], Assessment)
    assert isinstance(result[2], GradedAssessment)
    assert isinstance(result[3], Roadmap)
    assert isinstance(result[4], Course)
