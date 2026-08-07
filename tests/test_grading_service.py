from datetime import datetime, timezone

import pytest

from llm_engine.schemas import (
    Assessment,
    DomainQualitativeNote,
    ExamDomain,
    FillInBlankQuestion,
    FreeTextJudgment,
    FullTextQuestion,
    GradingDiagnosis,
    KnowledgeGap,
    MultiAnswerQuestion,
    QuestionOption,
    SingleAnswerQuestion,
    UserAnswer,
)
from llm_engine.services.grading import grade_assessment


def _option(option_id: str, text: str) -> QuestionOption:
    return QuestionOption(option_id=option_id, text=text)


def _single(question_id: str, domain_id: str, correct: str) -> SingleAnswerQuestion:
    return SingleAnswerQuestion(
        question_id=question_id,
        domain_id=domain_id,
        difficulty="medium",
        stem=f"Stem for {question_id}",
        options=[
            _option("A", "Right" if correct == "A" else "Wrong"),
            _option("B", "Right" if correct == "B" else "Wrong"),
            _option("C", "Right" if correct == "C" else "Wrong"),
            _option("D", "Right" if correct == "D" else "Wrong"),
        ],
        correct_option_id=correct,  # type: ignore[arg-type]
        explanation=f"{correct} is right.",
    )


def _multi(question_id: str, domain_id: str, correct_ids: list[str]) -> MultiAnswerQuestion:
    return MultiAnswerQuestion(
        question_id=question_id,
        domain_id=domain_id,
        difficulty="hard",
        stem=f"Stem for {question_id}",
        options=[_option("A", "A"), _option("B", "B"), _option("C", "C"), _option("D", "D")],
        correct_option_ids=correct_ids,  # type: ignore[arg-type]
        explanation="Correct options explained.",
    )


def _fill_blank(question_id: str, domain_id: str, accepted: list[str]) -> FillInBlankQuestion:
    return FillInBlankQuestion(
        question_id=question_id,
        domain_id=domain_id,
        difficulty="easy",
        stem=f"Stem for {question_id}",
        accepted_answers=accepted,
        explanation="Accepted answers explained.",
    )


def _full_text(question_id: str, domain_id: str, rubric: str) -> FullTextQuestion:
    return FullTextQuestion(
        question_id=question_id,
        domain_id=domain_id,
        difficulty="hard",
        stem=f"Stem for {question_id}",
        rubric=rubric,
        explanation="Rubric explained.",
    )


def _assessment() -> Assessment:
    return Assessment(
        assessment_id="assessment-1",
        syllabus_id="syllabus-1",
        topic="Cloud Architecture",
        certification="AWS SAA-C03",
        domains=[
            ExamDomain(domain_id="domain-a", name="Domain A", weight_percent=60.0, key_topics=["a"]),
            ExamDomain(domain_id="domain-b", name="Domain B", weight_percent=40.0, key_topics=["b"]),
            ExamDomain(domain_id="domain-c", name="Domain C", weight_percent=0.0, key_topics=["c"]),
        ],
        questions=[
            _single("q1", "domain-a", "A"),
            _single("q2", "domain-a", "B"),
            _single("q3", "domain-b", "C"),
        ],
        num_questions=3,
        created_at=datetime(2026, 7, 11, tzinfo=timezone.utc),
    )


def _mixed_assessment() -> Assessment:
    return Assessment(
        assessment_id="assessment-2",
        syllabus_id="syllabus-1",
        topic="Cloud Architecture",
        certification="AWS SAA-C03",
        domains=[
            ExamDomain(domain_id="domain-a", name="Domain A", weight_percent=100.0, key_topics=["a"]),
        ],
        questions=[
            _single("q1", "domain-a", "A"),
            _multi("q2", "domain-a", ["A", "B"]),
            _fill_blank("q3", "domain-a", ["STS"]),
            _full_text("q4", "domain-a", "Must mention least privilege."),
        ],
        num_questions=4,
        created_at=datetime(2026, 7, 11, tzinfo=timezone.utc),
    )


def _diagnosis(free_text_judgments: list[FreeTextJudgment] | None = None) -> GradingDiagnosis:
    return GradingDiagnosis(
        gaps=[
            KnowledgeGap(
                domain_id="domain-b",
                gap_summary="Cannot apply Domain B's core concept under time pressure.",
                severity="critical",
                evidence_question_ids=["q3", "not-a-question"],
            )
        ],
        per_domain_notes=[DomainQualitativeNote(domain_id="domain-a", note="Mixed.")],
        free_text_judgments=free_text_judgments or [],
        diagnostic_summary="Solid start, one critical gap.",
        strengths_summary="Handles Domain A fundamentals.",
    )


def test_scores_computed_deterministically(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def fake_structured_completion(*args: object, **kwargs: object) -> GradingDiagnosis:
        captured["user_prompt"] = args[2] if len(args) > 2 else kwargs["user_prompt"]
        return _diagnosis()

    monkeypatch.setattr("llm_engine.services.grading.structured_completion", fake_structured_completion)

    graded = grade_assessment(
        _assessment(),
        [
            UserAnswer(question_id="q1", selected_option_id="A"),   # correct
            UserAnswer(question_id="q2", selected_option_id="C"),   # wrong
            UserAnswer(question_id="q3", selected_option_id=None),  # skipped -> wrong, flagged
        ],
    )

    # weighted overall: domain-a 50% * 60 + domain-b 0% * 40, over weight 100 -> 30.0
    assert graded.overall_score_percent == 30.0

    assert [(r.question_id, r.correct, r.selected_option_id) for r in graded.question_results] == [
        ("q1", True, "A"),
        ("q2", False, "C"),
        ("q3", False, None),
    ]

    scores = {score.domain_id: score for score in graded.domain_scores}
    assert scores["domain-a"].questions_total == 2
    assert scores["domain-a"].questions_correct == 1.0
    assert scores["domain-a"].score_percent == 50.0
    assert scores["domain-a"].proficiency == "developing"
    assert scores["domain-b"].score_percent == 0.0
    assert scores["domain-b"].proficiency == "weak"
    assert scores["domain-c"].questions_total == 0  # zero-questions edge case
    assert scores["domain-c"].score_percent == 0.0

    # single/multi-answer ground truth is IN the prompt (LLM receives it, returns no MCQ numbers)
    assert "Correct: A | Learner chose: A | CORRECT" in captured["user_prompt"]
    assert "SKIPPED" in captured["user_prompt"]

    # unknown evidence id from the LLM is filtered out
    assert graded.gaps[0].evidence_question_ids == ["q3"]
    assert graded.diagnostic_summary == "Solid start, one critical gap."


def test_missing_answers_count_as_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "llm_engine.services.grading.structured_completion", lambda *a, **k: _diagnosis()
    )

    graded = grade_assessment(_assessment(), [UserAnswer(question_id="q1", selected_option_id="A")])

    results = {r.question_id: r for r in graded.question_results}
    assert results["q2"].correct is False
    assert results["q2"].selected_option_id is None
    assert results["q3"].selected_option_id is None


def test_unknown_answer_question_id_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "llm_engine.services.grading.structured_completion", lambda *a, **k: _diagnosis()
    )

    with pytest.raises(ValueError, match="Unknown question_id"):
        grade_assessment(_assessment(), [UserAnswer(question_id="missing", selected_option_id="A")])


def test_multi_answer_is_all_or_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "llm_engine.services.grading.structured_completion",
        lambda *a, **k: _diagnosis(),
    )

    graded = grade_assessment(
        _mixed_assessment(),
        [
            UserAnswer(question_id="q1", selected_option_id="A"),
            UserAnswer(question_id="q2", selected_option_ids=["A"]),  # partial overlap -> incorrect
            UserAnswer(question_id="q3", text_answer="STS"),
            UserAnswer(question_id="q4", text_answer="Least privilege limits access."),
        ],
    )

    results = {r.question_id: r for r in graded.question_results}
    assert results["q2"].correct is False
    assert results["q2"].score_percent == 0.0


def test_fill_in_blank_is_binary_and_full_text_is_partial(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_structured_completion(*args: object, **kwargs: object) -> GradingDiagnosis:
        return _diagnosis(
            free_text_judgments=[
                FreeTextJudgment(question_id="q3", score_percent=100.0, rationale="Matches STS."),
                FreeTextJudgment(question_id="q4", score_percent=60.0, rationale="Covers half the rubric."),
            ]
        )

    monkeypatch.setattr("llm_engine.services.grading.structured_completion", fake_structured_completion)

    graded = grade_assessment(
        _mixed_assessment(),
        [
            UserAnswer(question_id="q1", selected_option_id="A"),
            UserAnswer(question_id="q2", selected_option_ids=["A", "B"]),
            UserAnswer(question_id="q3", text_answer="STS"),
            UserAnswer(question_id="q4", text_answer="Limits access somewhat."),
        ],
    )

    results = {r.question_id: r for r in graded.question_results}
    assert results["q3"].correct is True
    assert results["q3"].score_percent == 100.0
    assert results["q4"].correct is False
    assert results["q4"].score_percent == 60.0

    # domain score is the mean of all 4 question score_percents: (100+100+100+60)/4 = 90.0
    domain_score = graded.domain_scores[0]
    assert domain_score.score_percent == 90.0
    assert domain_score.questions_correct == 3.6  # sum(score_percent)/100 = 360/100


def test_missing_free_text_judgment_defaults_to_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "llm_engine.services.grading.structured_completion",
        lambda *a, **k: _diagnosis(free_text_judgments=[]),  # LLM omitted q3 and q4
    )

    graded = grade_assessment(
        _mixed_assessment(),
        [
            UserAnswer(question_id="q1", selected_option_id="A"),
            UserAnswer(question_id="q2", selected_option_ids=["A", "B"]),
            UserAnswer(question_id="q3", text_answer="STS"),
            UserAnswer(question_id="q4", text_answer="Some answer."),
        ],
    )

    results = {r.question_id: r for r in graded.question_results}
    assert results["q3"].score_percent == 0.0
    assert results["q4"].score_percent == 0.0
