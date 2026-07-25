import llm_engine


def test_course_api_is_exported() -> None:
    for name in (
        "Course",
        "Lesson",
        "LessonSection",
        "LessonExample",
        "LessonPracticeQuestion",
        "generate_course",
        "generate_lesson",
    ):
        assert name in llm_engine.__all__, f"{name} missing from __all__"
        assert hasattr(llm_engine, name), f"{name} not importable from llm_engine"


def test_question_type_api_is_exported() -> None:
    for name in (
        "QuestionType",
        "QuestionTypeWeight",
        "SingleAnswerLLMQuestion",
        "MultiAnswerLLMQuestion",
        "FillInBlankLLMQuestion",
        "FullTextLLMQuestion",
        "SingleAnswerQuestion",
        "MultiAnswerQuestion",
        "FillInBlankQuestion",
        "FullTextQuestion",
    ):
        assert name in llm_engine.__all__, f"{name} missing from __all__"
        assert hasattr(llm_engine, name), f"{name} not importable from llm_engine"
