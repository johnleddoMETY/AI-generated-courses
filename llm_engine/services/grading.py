"""Grading: deterministic Python scoring first, then one LLM call for diagnosis only."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from llm_engine.client import structured_completion
from llm_engine.config import get_proficiency_thresholds
from llm_engine.prompts.grading_prompts import GRADING_SYSTEM_V1, build_grading_user_prompt
from llm_engine.schemas import (
    Assessment,
    DomainScore,
    GradedAssessment,
    GradingDiagnosis,
    KnowledgeGap,
    Proficiency,
    QuestionResult,
    UserAnswer,
)

logger = logging.getLogger(__name__)


def grade_assessment(assessment: Assessment, answers: list[UserAnswer]) -> GradedAssessment:
    """Grade an assessment: scores computed in Python, diagnosis by the LLM.

    Skipped answers (selected_option_id=None) and missing answers count as
    incorrect but keep selected_option_id=None so callers can flag them.
    Raises ValueError for answers referencing unknown question IDs.
    """
    questions_by_id = {question.question_id: question for question in assessment.questions}
    unknown = [answer.question_id for answer in answers if answer.question_id not in questions_by_id]
    if unknown:
        raise ValueError(f"Unknown question_id(s) in answers: {unknown}")

    answers_by_id = {answer.question_id: answer for answer in answers}
    question_results = [
        QuestionResult(
            question_id=question.question_id,
            domain_id=question.domain_id,
            correct=(
                answers_by_id.get(question.question_id) is not None
                and answers_by_id[question.question_id].selected_option_id
                == question.correct_option_id
            ),
            selected_option_id=(
                answers_by_id[question.question_id].selected_option_id
                if question.question_id in answers_by_id
                else None
            ),
            correct_option_id=question.correct_option_id,
            explanation=question.explanation,
        )
        for question in assessment.questions
    ]

    domain_scores = _compute_domain_scores(assessment, question_results)
    overall = _weighted_overall(domain_scores, question_results)

    diagnosis = structured_completion(
        GradingDiagnosis,
        GRADING_SYSTEM_V1,
        build_grading_user_prompt(
            questions_block=_format_questions_block(assessment, question_results),
            domain_scores_block=_format_domain_scores_block(domain_scores),
            overall_score_percent=overall,
        ),
        task="grading",
    )

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


def _compute_domain_scores(
    assessment: Assessment, question_results: list[QuestionResult]
) -> list[DomainScore]:
    weak_below, proficient_at = get_proficiency_thresholds()
    scores: list[DomainScore] = []
    for domain in assessment.domains:
        domain_results = [result for result in question_results if result.domain_id == domain.domain_id]
        total = len(domain_results)
        correct = sum(result.correct for result in domain_results)
        score_percent = round(100.0 * correct / total, 1) if total else 0.0
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
                questions_correct=correct,
                score_percent=score_percent,
                proficiency=proficiency,
            )
        )
    return scores


def _weighted_overall(
    domain_scores: list[DomainScore], question_results: list[QuestionResult]
) -> float:
    """Exam-weight-weighted overall score over domains that had questions."""
    scored = [score for score in domain_scores if score.questions_total > 0]
    weight_sum = sum(score.weight_percent for score in scored)
    if weight_sum > 0:
        return round(
            sum(score.score_percent * score.weight_percent for score in scored) / weight_sum, 1
        )
    if question_results:
        return round(100.0 * sum(result.correct for result in question_results) / len(question_results), 1)
    return 0.0


def _format_questions_block(
    assessment: Assessment, question_results: list[QuestionResult]
) -> str:
    results_by_id = {result.question_id: result for result in question_results}
    lines: list[str] = []
    for question in assessment.questions:
        result = results_by_id[question.question_id]
        selected = result.selected_option_id if result.selected_option_id else "SKIPPED"
        outcome = "CORRECT" if result.correct else "INCORRECT"
        options = "; ".join(f"{option.option_id}) {option.text}" for option in question.options)
        lines.append(
            f"[{question.question_id}] domain={question.domain_id} "
            f"difficulty={question.difficulty}\n"
            f"  Stem: {question.stem}\n"
            f"  Options: {options}\n"
            f"  Correct: {question.correct_option_id} | Learner chose: {selected} | {outcome}"
        )
    return "\n".join(lines)


def _format_domain_scores_block(domain_scores: list[DomainScore]) -> str:
    return "\n".join(
        f"- {score.domain_id} ({score.domain_name}, {score.weight_percent:.0f}% of exam): "
        f"{score.questions_correct}/{score.questions_total} correct = "
        f"{score.score_percent}% -> {score.proficiency}"
        for score in domain_scores
    )


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
