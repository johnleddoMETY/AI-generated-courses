from datetime import datetime, timezone

import pytest

from llm_engine.exceptions import StructuredOutputError
from llm_engine.schemas import (
    AssessmentLLMResponse,
    ExamDomain,
    FillInBlankLLMQuestion,
    FullTextLLMQuestion,
    LLMQuestionOption,
    MultiAnswerLLMQuestion,
    QuestionTypeWeight,
    SingleAnswerLLMQuestion,
    Syllabus,
)
from llm_engine.services.assessment import (
    _allocate_question_types,
    _allocate_questions,
    generate_assessment,
)


def _domain(domain_id: str, weight: float) -> ExamDomain:
    return ExamDomain(domain_id=domain_id, name=domain_id.title(), weight_percent=weight, key_topics=["t"])


def _type_mix(*pairs: tuple[str, float]) -> list[QuestionTypeWeight]:
    return [QuestionTypeWeight(question_type=qtype, weight_percent=weight) for qtype, weight in pairs]


def _syllabus(question_type_mix: list[QuestionTypeWeight] | None = None) -> Syllabus:
    return Syllabus(
        syllabus_id="syllabus-1",
        topic="Cloud Architecture",
        certification="AWS SAA-C03",
        exam_code="SAA-C03",
        domains=[_domain("domain-a", 50.0), _domain("domain-b", 50.0)],
        question_type_mix=question_type_mix or _type_mix(("single_answer", 100.0)),
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


def _single(domain_id: str = "domain-a", options: list[LLMQuestionOption] | None = None) -> SingleAnswerLLMQuestion:
    return SingleAnswerLLMQuestion(
        domain_id=domain_id,
        difficulty="easy",
        stem="Which option is correct?",
        options=options if options is not None else _options(),
        correct_option_id="A",
        explanation="A is right; B, C, D reflect common misconceptions.",
    )


def _multi(domain_id: str = "domain-a", correct_ids: list[str] | None = None) -> MultiAnswerLLMQuestion:
    return MultiAnswerLLMQuestion(
        domain_id=domain_id,
        difficulty="hard",
        stem="Select all that apply: which are correct?",
        options=_options(),
        correct_option_ids=correct_ids if correct_ids is not None else ["A", "B"],
        explanation="A and B are right; C, D are common misconceptions.",
    )


def _fill_blank(domain_id: str = "domain-a", accepted: list[str] | None = None) -> FillInBlankLLMQuestion:
    return FillInBlankLLMQuestion(
        domain_id=domain_id,
        difficulty="easy",
        stem="Which service issues temporary credentials?",
        accepted_answers=accepted if accepted is not None else ["STS"],
        explanation="STS issues short-lived credentials.",
    )


def _full_text(domain_id: str = "domain-a", rubric: str = "Must mention least privilege.") -> FullTextLLMQuestion:
    return FullTextLLMQuestion(
        domain_id=domain_id,
        difficulty="hard",
        stem="Explain least privilege.",
        rubric=rubric,
        explanation="Least privilege limits access to only what's needed.",
    )


def test_allocation_uses_largest_remainder() -> None:
    domains = [_domain("a", 30.0), _domain("b", 26.0), _domain("c", 24.0), _domain("d", 20.0)]
    assert _allocate_questions(domains, 12) == {"a": 4, "b": 3, "c": 3, "d": 2}


def test_allocation_gives_zero_weight_domains_zero_questions() -> None:
    domains = [_domain("a", 100.0), _domain("b", 0.0)]
    assert _allocate_questions(domains, 5) == {"a": 5, "b": 0}


def test_type_allocation_uses_largest_remainder() -> None:
    mix = _type_mix(("single_answer", 60.0), ("multi_answer", 25.0), ("fill_in_blank", 15.0))
    assert _allocate_question_types(mix, 20) == {"single_answer": 12, "multi_answer": 5, "fill_in_blank": 3}


def test_type_allocation_gives_zero_weight_types_zero_questions() -> None:
    mix = _type_mix(("single_answer", 100.0), ("multi_answer", 0.0))
    assert _allocate_question_types(mix, 5) == {"single_answer": 5, "multi_answer": 0}


def test_generate_assessment_assembles_ids_and_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_structured_completion(*args: object, **kwargs: object) -> AssessmentLLMResponse:
        return AssessmentLLMResponse(questions=[_single("domain-a"), _single("domain-b")])

    monkeypatch.setattr(
        "llm_engine.services.assessment.structured_completion", fake_structured_completion
    )

    assessment = generate_assessment(_syllabus(), num_questions=2)

    assert len(assessment.assessment_id) == 36
    assert assessment.syllabus_id == "syllabus-1"
    assert assessment.num_questions == 2
    assert [d.domain_id for d in assessment.domains] == ["domain-a", "domain-b"]
    assert all(len(q.question_id) == 36 for q in assessment.questions)
    assert all(q.question_type == "single_answer" for q in assessment.questions)


def test_generate_assessment_assembles_all_four_types(monkeypatch: pytest.MonkeyPatch) -> None:
    mix = _type_mix(
        ("single_answer", 25.0), ("multi_answer", 25.0), ("fill_in_blank", 25.0), ("full_text", 25.0)
    )

    def fake_structured_completion(*args: object, **kwargs: object) -> AssessmentLLMResponse:
        return AssessmentLLMResponse(
            questions=[_single(), _multi(), _fill_blank(), _full_text()]
        )

    monkeypatch.setattr(
        "llm_engine.services.assessment.structured_completion", fake_structured_completion
    )

    assessment = generate_assessment(_syllabus(mix), num_questions=4)

    types = {q.question_type for q in assessment.questions}
    assert types == {"single_answer", "multi_answer", "fill_in_blank", "full_text"}
    multi_q = next(q for q in assessment.questions if q.question_type == "multi_answer")
    assert multi_q.correct_option_ids == ["A", "B"]
    fill_q = next(q for q in assessment.questions if q.question_type == "fill_in_blank")
    assert fill_q.accepted_answers == ["STS"]
    text_q = next(q for q in assessment.questions if q.question_type == "full_text")
    assert text_q.rubric == "Must mention least privilege."


def test_post_validation_failure_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    bad = AssessmentLLMResponse(questions=[_single("unknown-domain")])
    good = AssessmentLLMResponse(questions=[_single("domain-a")])
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
    bad = AssessmentLLMResponse(questions=[_single(options=three_options)])
    good = AssessmentLLMResponse(questions=[_single()])
    responses = [bad, good]

    monkeypatch.setattr(
        "llm_engine.services.assessment.structured_completion",
        lambda *args, **kwargs: responses.pop(0),
    )

    assessment = generate_assessment(_syllabus(), num_questions=1)

    assert len(assessment.questions[0].options) == 4
    assert not responses


def test_multi_answer_needs_two_correct_ids_triggers_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    mix = _type_mix(("multi_answer", 100.0))
    bad = AssessmentLLMResponse(questions=[_multi(correct_ids=["A"])])
    good = AssessmentLLMResponse(questions=[_multi(correct_ids=["A", "B"])])
    responses = [bad, good]

    monkeypatch.setattr(
        "llm_engine.services.assessment.structured_completion",
        lambda *args, **kwargs: responses.pop(0),
    )

    assessment = generate_assessment(_syllabus(mix), num_questions=1)

    assert assessment.questions[0].correct_option_ids == ["A", "B"]
    assert not responses


def test_fill_in_blank_needs_accepted_answers_triggers_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    mix = _type_mix(("fill_in_blank", 100.0))
    bad = AssessmentLLMResponse(questions=[_fill_blank(accepted=[])])
    good = AssessmentLLMResponse(questions=[_fill_blank(accepted=["STS"])])
    responses = [bad, good]

    monkeypatch.setattr(
        "llm_engine.services.assessment.structured_completion",
        lambda *args, **kwargs: responses.pop(0),
    )

    assessment = generate_assessment(_syllabus(mix), num_questions=1)

    assert assessment.questions[0].accepted_answers == ["STS"]
    assert not responses


def test_type_count_mismatch_triggers_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    mix = _type_mix(("single_answer", 50.0), ("multi_answer", 50.0))
    bad = AssessmentLLMResponse(questions=[_single(), _single()])  # should be 1 single + 1 multi
    good = AssessmentLLMResponse(questions=[_single(), _multi()])
    responses = [bad, good]

    monkeypatch.setattr(
        "llm_engine.services.assessment.structured_completion",
        lambda *args, **kwargs: responses.pop(0),
    )

    assessment = generate_assessment(_syllabus(mix), num_questions=2)

    types = sorted(q.question_type for q in assessment.questions)
    assert types == ["multi_answer", "single_answer"]
    assert not responses


def test_always_invalid_raises_structured_output_error(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = 0

    def fake_structured_completion(*args: object, **kwargs: object) -> AssessmentLLMResponse:
        nonlocal call_count
        call_count += 1
        return AssessmentLLMResponse(questions=[_single("unknown-domain")])

    monkeypatch.setattr(
        "llm_engine.services.assessment.structured_completion", fake_structured_completion
    )

    with pytest.raises(StructuredOutputError):
        generate_assessment(_syllabus(), num_questions=1)

    assert call_count == 3  # 1 initial + 2 post-validation retries
