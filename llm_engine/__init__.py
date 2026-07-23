"""llm_engine: LLM pipeline for adaptive certification course generation.

Public API: the four stage functions, the pipeline orchestrator, all
domain schemas, and the typed exceptions.
"""

from llm_engine.exceptions import LLMCallError, LLMEngineError, StructuredOutputError
from llm_engine.schemas import (
    Assessment,
    Course,
    DomainScore,
    ExamDomain,
    GradedAssessment,
    KnowledgeGap,
    Lesson,
    LessonExample,
    LessonPracticeQuestion,
    LessonSection,
    Question,
    QuestionOption,
    QuestionResult,
    Roadmap,
    RoadmapItem,
    SkippedDomain,
    StudyWeek,
    Syllabus,
    UserAnswer,
)
from llm_engine.services import (
    generate_assessment,
    generate_course,
    generate_lesson,
    generate_roadmap,
    generate_syllabus,
    grade_assessment,
    run_full_pipeline,
)

__all__ = [
    "Assessment",
    "Course",
    "DomainScore",
    "ExamDomain",
    "GradedAssessment",
    "KnowledgeGap",
    "Lesson",
    "LessonExample",
    "LessonPracticeQuestion",
    "LessonSection",
    "LLMCallError",
    "LLMEngineError",
    "Question",
    "QuestionOption",
    "QuestionResult",
    "Roadmap",
    "RoadmapItem",
    "SkippedDomain",
    "StructuredOutputError",
    "StudyWeek",
    "Syllabus",
    "UserAnswer",
    "generate_assessment",
    "generate_course",
    "generate_lesson",
    "generate_roadmap",
    "generate_syllabus",
    "grade_assessment",
    "run_full_pipeline",
]
