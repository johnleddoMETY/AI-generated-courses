"""Grading: deterministic Python scoring for single/multi-answer questions,
one LLM call for free-text judgments (fill_in_blank/full_text) plus
qualitative diagnosis."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from llm_engine.client import structured_completion
from llm_engine.config import get_proficiency_thresholds
from llm_engine.prompts.grading_prompts import GRADING_SYSTEM_V1, build_grading_user_prompt
from llm_engine.schemas import (
    Assessment,
    DomainScore,
    FreeTextJudgment,
    GradedAssessment,
    GradingDiagnosis,
    KnowledgeGap,
    Proficiency,
    Question,
    QuestionResult,
    UserAnswer,
)

logger = logging.getLogger(__name__)

_FREE_TEXT_TYPES = ("fill_in_blank", "full_text")


def grade_assessment(assessment: Assessment, answers: list[UserAnswer]) -> GradedAssessment:
    """Grade an assessment: single/multi-answer scores computed in Python,
    free-text scores and qualitative diagnosis from one LLM call.

    Skipped answers (no matching UserAnswer, or a None/empty type-specific
    field) count as incorrect. Raises ValueError for answers referencing
    unknown question IDs.
    """
    questions_by_id: dict[str, Question] = {q.question_id: q for q in assessment.questions}
    unknown = [answer.question_id for answer in answers if answer.question_id not in questions_by_id]
    if unknown:
        raise ValueError(f"Unknown question_id(s) in answers: {unknown}")

    answers_by_id = {answer.question_id: answer for answer in answers}
    question_results = [
        _score_question(question, answers_by_id.get(question.question_id))
        for question in assessment.questions
    ]

    diagnosis = structured_completion(
        GradingDiagnosis,
        GRADING_SYSTEM_V1,
        build_grading_user_prompt(
            scored_questions_block=_format_scored_questions_block(assessment, question_results),
            free_text_block=_format_free_text_block(assessment, question_results),
        ),
        task="grading",
    )

    question_results = _merge_free_text_judgments(question_results, diagnosis.free_text_judgments)
    domain_scores = _compute_domain_scores(assessment, question_results)
    overall = _weighted_overall(domain_scores, question_results)

    gaps = _filter_gap_evidence(diagnosis.gaps, set(questions_by_id))

    return GradedAssessment(
        assessment_id=assessment.assessment_id,
        overall_score_percent=overall,
        question_results=question_results,
        domain_scores=domain_scores,
        gaps=gaps,
        diagnostic_summary=diagnosis.diagnostic_summary,
        strengths_summary=diagnosis.strengths_summary,
        graded_at=datetime.now(timezone.utc),
    )


def _score_question(question: Question, answer: UserAnswer | None) -> QuestionResult:
    """Score one question. single_answer/multi_answer are scored here;
    fill_in_blank/full_text get a 0.0 placeholder that
    _merge_free_text_judgments fills in afterward."""
    if question.question_type == "single_answer":
        selected = answer.selected_option_id if answer else None
        correct = selected is not None and selected == question.correct_option_id
        return QuestionResult(
            question_id=question.question_id,
            domain_id=question.domain_id,
            question_type=question.question_type,
            correct=correct,
            score_percent=100.0 if correct else 0.0,
            selected_option_id=selected,
            correct_option_id=question.correct_option_id,
            explanation=question.explanation,
        )
    if question.question_type == "multi_answer":
        selected_ids = answer.selected_option_ids if answer and answer.selected_option_ids else None
        correct = selected_ids is not None and set(selected_ids) == set(question.correct_option_ids)
        return QuestionResult(
            question_id=question.question_id,
            domain_id=question.domain_id,
            question_type=question.question_type,
            correct=correct,
            score_percent=100.0 if correct else 0.0,
            selected_option_ids=selected_ids,
            correct_option_ids=question.correct_option_ids,
            explanation=question.explanation,
        )
    text_answer = answer.text_answer if answer else None
    return QuestionResult(
        question_id=question.question_id,
        domain_id=question.domain_id,
        question_type=question.question_type,
        correct=False,
        score_percent=0.0,
        text_answer=text_answer,
        explanation=question.explanation,
    )


def _merge_free_text_judgments(
    question_results: list[QuestionResult], judgments: list[FreeTextJudgment]
) -> list[QuestionResult]:
    """Apply the LLM's free-text scores onto the matching placeholder results."""
    judgments_by_id = {judgment.question_id: judgment for judgment in judgments}
    merged: list[QuestionResult] = []
    for result in question_results:
        if result.question_type not in _FREE_TEXT_TYPES:
            merged.append(result)
            continue
        judgment = judgments_by_id.get(result.question_id)
        if judgment is None:
            logger.warning(
                "No free_text_judgment returned for question_id=%s; scoring 0.",
                result.question_id,
            )
            merged.append(result)
            continue
        score_percent = max(0.0, min(100.0, judgment.score_percent))
        if result.question_type == "fill_in_blank":
            score_percent = 100.0 if score_percent >= 50.0 else 0.0
        merged.append(
            result.model_copy(update={"score_percent": score_percent, "correct": score_percent == 100.0})
        )
    return merged


def _compute_domain_scores(
    assessment: Assessment, question_results: list[QuestionResult]
) -> list[DomainScore]:
    weak_below, proficient_at = get_proficiency_thresholds()
    scores: list[DomainScore] = []
    for domain in assessment.domains:
        domain_results = [result for result in question_results if result.domain_id == domain.domain_id]
        total = len(domain_results)
        score_percent = (
            round(sum(result.score_percent for result in domain_results) / total, 1) if total else 0.0
        )
        questions_correct = round(sum(result.score_percent for result in domain_results) / 100, 2)
        proficiency: Proficiency = (
            "weak"
            if score_percent < weak_below
            else "developing"
            if score_percent < proficient_at
            else "proficient"
        )
        scores.append(
            DomainScore(
                domain_id=domain.domain_id,
                domain_name=domain.name,
                weight_percent=domain.weight_percent,
                questions_total=total,
                questions_correct=questions_correct,
                score_percent=score_percent,
                proficiency=proficiency,
            )
        )
    return scores


def _weighted_overall(domain_scores: list[DomainScore], question_results: list[QuestionResult]) -> float:
    """Exam-weight-weighted overall score over domains that had questions."""
    scored = [score for score in domain_scores if score.questions_total > 0]
    weight_sum = sum(score.weight_percent for score in scored)
    if weight_sum > 0:
        return round(
            sum(score.score_percent * score.weight_percent for score in scored) / weight_sum, 1
        )
    if question_results:
        return round(sum(result.score_percent for result in question_results) / len(question_results), 1)
    return 0.0


def _format_scored_questions_block(assessment: Assessment, question_results: list[QuestionResult]) -> str:
    """Ground-truth block for single_answer/multi_answer questions: already scored, LLM must not recompute."""
    results_by_id = {result.question_id: result for result in question_results}
    lines: list[str] = []
    for question in assessment.questions:
        if question.question_type not in ("single_answer", "multi_answer"):
            continue
        result = results_by_id[question.question_id]
        outcome = "CORRECT" if result.correct else "INCORRECT"
        options = "; ".join(f"{option.option_id}) {option.text}" for option in question.options)
        if question.question_type == "single_answer":
            selected = result.selected_option_id or "SKIPPED"
            correct_desc = question.correct_option_id
        else:
            selected = ", ".join(result.selected_option_ids) if result.selected_option_ids else "SKIPPED"
            correct_desc = ", ".join(question.correct_option_ids)
        lines.append(
            f"[{question.question_id}] domain={question.domain_id} "
            f"difficulty={question.difficulty}\n"
            f"  Stem: {question.stem}\n"
            f"  Options: {options}\n"
            f"  Correct: {correct_desc} | Learner chose: {selected} | {outcome}"
        )
    return "\n".join(lines) if lines else "(none)"


def _format_free_text_block(assessment: Assessment, question_results: list[QuestionResult]) -> str:
    """Block of fill_in_blank/full_text questions needing an LLM judgment."""
    results_by_id = {result.question_id: result for result in question_results}
    lines: list[str] = []
    for question in assessment.questions:
        if question.question_type not in _FREE_TEXT_TYPES:
            continue
        result = results_by_id[question.question_id]
        answer_text = result.text_answer or "SKIPPED"
        if question.question_type == "fill_in_blank":
            reference = f"Accepted answers: {'; '.join(question.accepted_answers)}"
        else:
            reference = f"Rubric: {question.rubric}"
        lines.append(
            f"[{question.question_id}] domain={question.domain_id} "
            f"question_type={question.question_type}\n"
            f"  Stem: {question.stem}\n"
            f"  {reference}\n"
            f"  Learner answer: {answer_text}"
        )
    return "\n".join(lines) if lines else "(none)"


def _filter_gap_evidence(gaps: list[KnowledgeGap], known_ids: set[str]) -> list[KnowledgeGap]:
    """Drop evidence question IDs the LLM hallucinated; keep the gap itself."""
    filtered: list[KnowledgeGap] = []
    for gap in gaps:
        valid_ids = [qid for qid in gap.evidence_question_ids if qid in known_ids]
        dropped = set(gap.evidence_question_ids) - set(valid_ids)
        if dropped:
            logger.warning("Dropping unknown evidence_question_ids from gap: %s", sorted(dropped))
        filtered.append(gap.model_copy(update={"evidence_question_ids": valid_ids}))
    return filtered
