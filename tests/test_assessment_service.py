from datetime import datetime, timezone

import pytest

from llm_engine.exceptions import StructuredOutputError
from llm_engine.schemas import (
    AssessmentLLMResponse,
    ExamDomain,
    LLMQuestion,
    LLMQuestionOption,
    Syllabus,
)
from llm_engine.services.assessment import _allocate_questions, generate_assessment


def _domain(domain_id: str, weight: float) -> ExamDomain:
    return ExamDomain(domain_id=domain_id, name=domain_id.title(), weight_percent=weight, key_topics=["t"])


def _syllabus() -> Syllabus:
    return Syllabus(
        syllabus_id="syllabus-1",
        topic="Cloud Architecture",
        certification="AWS SAA-C03",
        exam_code="SAA-C03",
        domains=[_domain("domain-a", 50.0), _domain("domain-b", 50.0)],
        source_note="Test syllabus.",
        created_at=datetime(2026, 7, 11, tzinfo=timezone.utc),
    )


def _options(correct: str = "A") -> list[LLMQuestionOption]:
    return [
        LLMQuestionOption(option_id="A", text="Right" if correct == "A" else "Wrong"),
        LLMQuestionOption(option_id="B", text="Right" if correct == "B" else "Wrong"),
        LLMQuestionOption(option_id="C", text="Wrong"),
        LLMQuestionOption(option_id="D", text="Wrong"),
    ]


def _question(domain_id: str = "domain-a", options: list[LLMQuestionOption] | None = None) -> LLMQuestion:
    return LLMQuestion(
        domain_id=domain_id,
        difficulty="easy",
        stem="Which option is correct?",
        options=options if options is not None else _options(),
        correct_option_id="A",
        explanation="A is right; B, C, D reflect common misconceptions.",
    )


def test_allocation_uses_largest_remainder() -> None:
    domains = [_domain("a", 30.0), _domain("b", 26.0), _domain("c", 24.0), _domain("d", 20.0)]
    assert _allocate_questions(domains, 12) == {"a": 4, "b": 3, "c": 3, "d": 2}


def test_allocation_gives_zero_weight_domains_zero_questions() -> None:
    domains = [_domain("a", 100.0), _domain("b", 0.0)]
    assert _allocate_questions(domains, 5) == {"a": 5, "b": 0}


def test_generate_assessment_assembles_ids_and_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_structured_completion(*args: object, **kwargs: object) -> AssessmentLLMResponse:
        return AssessmentLLMResponse(questions=[_question("domain-a"), _question("domain-b")])

    monkeypatch.setattr(
        "llm_engine.services.assessment.structured_completion", fake_structured_completion
    )

    assessment = generate_assessment(_syllabus(), num_questions=2)

    assert len(assessment.assessment_id) == 36
    assert assessment.syllabus_id == "syllabus-1"
    assert assessment.num_questions == 2
    assert [d.domain_id for d in assessment.domains] == ["domain-a", "domain-b"]
    assert all(len(q.question_id) == 36 for q in assessment.questions)
    assert all(len(q.options) == 4 for q in assessment.questions)


def test_post_validation_failure_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    bad = AssessmentLLMResponse(questions=[_question("unknown-domain")])
    good = AssessmentLLMResponse(questions=[_question("domain-a")])
    responses = [bad, good]
    prompts: list[str] = []

    def fake_structured_completion(*args: object, **kwargs: object) -> AssessmentLLMResponse:
        prompts.append(args[2] if len(args) > 2 else kwargs["user_prompt"])
        return responses.pop(0)

    monkeypatch.setattr(
        "llm_engine.services.assessment.structured_completion", fake_structured_completion
    )

    assessment = generate_assessment(_syllabus(), num_questions=1)

    assert assessment.questions[0].domain_id == "domain-a"
    assert not responses
    assert "unknown-domain" in prompts[1]  # error fed back into retry prompt


def test_wrong_option_count_triggers_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    three_options = _options()[:3]
    bad = AssessmentLLMResponse(questions=[_question(options=three_options)])
    good = AssessmentLLMResponse(questions=[_question()])
    responses = [bad, good]

    monkeypatch.setattr(
        "llm_engine.services.assessment.structured_completion",
        lambda *args, **kwargs: responses.pop(0),
    )

    assessment = generate_assessment(_syllabus(), num_questions=1)

    assert len(assessment.questions[0].options) == 4
    assert not responses


def test_always_invalid_raises_structured_output_error(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = 0

    def fake_structured_completion(*args: object, **kwargs: object) -> AssessmentLLMResponse:
        nonlocal call_count
        call_count += 1
        return AssessmentLLMResponse(questions=[_question("unknown-domain")])

    monkeypatch.setattr(
        "llm_engine.services.assessment.structured_completion", fake_structured_completion
    )

    with pytest.raises(StructuredOutputError):
        generate_assessment(_syllabus(), num_questions=1)

    assert call_count == 3  # 1 initial + 2 post-validation retries
