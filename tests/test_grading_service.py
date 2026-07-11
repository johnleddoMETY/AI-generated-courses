from datetime import datetime, timezone

import pytest

from llm_engine.schemas import (
    Assessment,
    DomainQualitativeNote,
    ExamDomain,
    GradingDiagnosis,
    KnowledgeGap,
    Question,
    QuestionOption,
    UserAnswer,
)
from llm_engine.services.grading import grade_assessment


def _option(option_id: str, text: str) -> QuestionOption:
    return QuestionOption(option_id=option_id, text=text)


def _question(question_id: str, domain_id: str, correct: str) -> Question:
    return Question(
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
            _question("q1", "domain-a", "A"),
            _question("q2", "domain-a", "B"),
            _question("q3", "domain-b", "C"),
        ],
        num_questions=3,
        created_at=datetime(2026, 7, 11, tzinfo=timezone.utc),
    )


def _diagnosis() -> GradingDiagnosis:
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
    assert scores["domain-a"].questions_correct == 1
    assert scores["domain-a"].score_percent == 50.0
    assert scores["domain-a"].proficiency == "developing"
    assert scores["domain-b"].score_percent == 0.0
    assert scores["domain-b"].proficiency == "weak"
    assert scores["domain-c"].questions_total == 0  # zero-questions edge case
    assert scores["domain-c"].score_percent == 0.0

    # computed scores are IN the prompt (LLM receives ground truth, returns no numbers)
    assert "30.0" in captured["user_prompt"]
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
