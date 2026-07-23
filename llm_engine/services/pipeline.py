"""End-to-end pipeline orchestrator for the demo CLI and tests."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from llm_engine.schemas import Assessment, Course, GradedAssessment, Roadmap, Syllabus, UserAnswer
from llm_engine.services.assessment import generate_assessment
from llm_engine.services.course import generate_course
from llm_engine.services.grading import grade_assessment
from llm_engine.services.roadmap import generate_roadmap
from llm_engine.services.syllabus import generate_syllabus


def run_full_pipeline(
    topic: str,
    certification: str,
    answer_provider: Callable[[Assessment], list[UserAnswer]],
    exam_date: date | None = None,
    num_questions: int = 12,
) -> tuple[Syllabus, Assessment, GradedAssessment, Roadmap, Course]:
    """Run all five pipeline stages, delegating answer collection to a callable.

    answer_provider receives the generated Assessment and returns the
    learner's answers — the demo CLI plugs in interactive or random answers
    here, and tests plug in crafted ones.
    """
    syllabus = generate_syllabus(topic, certification)
    assessment = generate_assessment(syllabus, num_questions=num_questions, exam_date=exam_date)
    answers = answer_provider(assessment)
    graded = grade_assessment(assessment, answers)
    roadmap = generate_roadmap(syllabus, graded, exam_date=exam_date)
    course = generate_course(roadmap)
    return syllabus, assessment, graded, roadmap, course
