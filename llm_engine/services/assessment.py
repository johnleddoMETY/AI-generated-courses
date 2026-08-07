"""Assessment generation: allocation math in Python, question writing by the LLM."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from uuid import uuid4

from llm_engine.client import structured_completion
from llm_engine.config import MAX_VALIDATION_RETRIES
from llm_engine.exceptions import StructuredOutputError
from llm_engine.prompts.assessment_prompts import (
    ASSESSMENT_SYSTEM_V1,
    build_assessment_retry_suffix,
    build_assessment_user_prompt,
)
from llm_engine.schemas import (
    Assessment,
    AssessmentLLMResponse,
    ExamDomain,
    FillInBlankQuestion,
    FullTextQuestion,
    MultiAnswerQuestion,
    Question,
    QuestionOption,
    QuestionTypeWeight,
    SingleAnswerQuestion,
    Syllabus,
)

logger = logging.getLogger(__name__)

_EXPECTED_OPTION_IDS = {"A", "B", "C", "D"}
_MCQ_TYPES = ("single_answer", "multi_answer")


def generate_assessment(
    syllabus: Syllabus,
    num_questions: int = 12,
    exam_date: date | None = None,
) -> Assessment:
    """Generate an assessment distributed across syllabus domains and question types.

    Both the per-domain allocation and the per-question-type allocation are
    computed here (largest-remainder method) and stated in the prompt; the
    LLM never does the math. LLM output is post-validated in code (correct
    shape per question_type, known domain_id, counts matching both
    allocations) and regenerated with the errors fed back, up to
    MAX_VALIDATION_RETRIES times, before raising StructuredOutputError.
    """
    domain_allocation = _allocate_questions(syllabus.domains, num_questions)
    type_allocation = _allocate_question_types(syllabus.question_type_mix, num_questions)
    base_prompt = _build_base_prompt(
        syllabus, domain_allocation, type_allocation, num_questions, exam_date
    )

    user_prompt = base_prompt
    errors: list[str] = []
    for attempt in range(1 + MAX_VALIDATION_RETRIES):
        llm_response = structured_completion(
            AssessmentLLMResponse,
            ASSESSMENT_SYSTEM_V1,
            user_prompt,
            task="assessment",
        )
        errors = _post_validate(llm_response, syllabus, type_allocation)
        if not errors:
            return _assemble(syllabus, llm_response)
        logger.warning(
            "Assessment post-validation failed attempt=%d/%d: %s",
            attempt + 1,
            1 + MAX_VALIDATION_RETRIES,
            errors,
        )
        user_prompt = base_prompt + build_assessment_retry_suffix(errors)

    raise StructuredOutputError(
        f"Assessment failed post-validation after {1 + MAX_VALIDATION_RETRIES} "
        f"attempts. Last errors: {errors}"
    )


def _largest_remainder(weights: dict[str, float], total: int) -> dict[str, int]:
    """Distribute `total` across weights' keys proportional to weight (largest remainder)."""
    total_weight = sum(weights.values())
    if total_weight <= 0:
        base = total // len(weights)
        counts = {key: base for key in weights}
        for key in list(weights)[: total - base * len(weights)]:
            counts[key] += 1
        return counts

    exact = {key: total * weight / total_weight for key, weight in weights.items()}
    counts = {key: int(value) for key, value in exact.items()}
    shortfall = total - sum(counts.values())
    by_remainder = sorted(exact, key=lambda key: exact[key] - counts[key], reverse=True)
    for key in by_remainder[:shortfall]:
        counts[key] += 1
    return counts


def _allocate_questions(domains: list[ExamDomain], num_questions: int) -> dict[str, int]:
    """Distribute num_questions across domains proportional to weight."""
    weights = {domain.domain_id: domain.weight_percent for domain in domains}
    return _largest_remainder(weights, num_questions)


def _allocate_question_types(
    question_type_mix: list[QuestionTypeWeight], num_questions: int
) -> dict[str, int]:
    """Distribute num_questions across question types proportional to weight."""
    weights = {item.question_type: item.weight_percent for item in question_type_mix}
    return _largest_remainder(weights, num_questions)


def _build_base_prompt(
    syllabus: Syllabus,
    domain_allocation: dict[str, int],
    type_allocation: dict[str, int],
    num_questions: int,
    exam_date: date | None,
) -> str:
    domains_block = "\n".join(
        f"- {domain.domain_id}: {domain.name} ({domain.weight_percent:.0f}% of exam) — "
        f"key topics: {', '.join(domain.key_topics)}"
        for domain in syllabus.domains
    )
    allocation_block = "\n".join(
        f"- {domain_id}: {count} question(s)"
        for domain_id, count in domain_allocation.items()
        if count > 0
    )
    type_allocation_block = "\n".join(
        f"- {question_type}: {count} question(s)"
        for question_type, count in type_allocation.items()
        if count > 0
    )
    exam_date_line = (
        f"The learner takes this exam on {exam_date.isoformat()}." if exam_date else ""
    )
    return build_assessment_user_prompt(
        topic=syllabus.topic,
        certification=syllabus.certification,
        domains_block=domains_block,
        allocation_block=allocation_block,
        type_allocation_block=type_allocation_block,
        num_questions=num_questions,
        exam_date_line=exam_date_line,
    )


def _post_validate(
    llm_response: AssessmentLLMResponse,
    syllabus: Syllabus,
    type_allocation: dict[str, int],
) -> list[str]:
    """Check LLM questions against rules strict mode cannot express; return error strings."""
    known_domain_ids = {domain.domain_id for domain in syllabus.domains}
    errors: list[str] = []
    type_counts: dict[str, int] = {}

    for index, question in enumerate(llm_response.questions, start=1):
        type_counts[question.question_type] = type_counts.get(question.question_type, 0) + 1

        if question.question_type in _MCQ_TYPES:
            option_ids = [option.option_id for option in question.options]
            if len(question.options) != 4 or set(option_ids) != _EXPECTED_OPTION_IDS:
                errors.append(
                    f"Question {index}: must have exactly 4 options with option_ids "
                    f"A, B, C, D (got {option_ids})."
                )
            elif question.question_type == "single_answer":
                if question.correct_option_id not in option_ids:
                    errors.append(
                        f"Question {index}: correct_option_id "
                        f"{question.correct_option_id!r} is not among its options."
                    )
            else:
                if len(question.correct_option_ids) < 2:
                    errors.append(
                        f"Question {index}: multi_answer must have 2 or more "
                        f"correct_option_ids (got {question.correct_option_ids})."
                    )
                elif not set(question.correct_option_ids) <= set(option_ids):
                    errors.append(
                        f"Question {index}: correct_option_ids "
                        f"{question.correct_option_ids!r} are not all among its options."
                    )
        elif question.question_type == "fill_in_blank":
            if not question.accepted_answers:
                errors.append(f"Question {index}: fill_in_blank must have accepted_answers.")
        elif question.question_type == "full_text":
            if not question.rubric.strip():
                errors.append(f"Question {index}: full_text must have a non-empty rubric.")

        if question.domain_id not in known_domain_ids:
            errors.append(
                f"Question {index}: domain_id {question.domain_id!r} is not in the syllabus "
                f"(valid: {sorted(known_domain_ids)})."
            )

    expected_types = {qtype for qtype, count in type_allocation.items() if count > 0}
    for question_type in expected_types | set(type_counts):
        expected = type_allocation.get(question_type, 0)
        actual = type_counts.get(question_type, 0)
        if actual != expected:
            errors.append(
                f"question_type {question_type!r}: expected {expected} question(s), got {actual}."
            )

    return errors


def _assemble(syllabus: Syllabus, llm_response: AssessmentLLMResponse) -> Assessment:
    """Attach UUIDs and the domain snapshot to validated LLM questions."""
    questions: list[Question] = []
    for llm_question in llm_response.questions:
        question_id = str(uuid4())
        if llm_question.question_type == "single_answer":
            questions.append(
                SingleAnswerQuestion(
                    question_id=question_id,
                    domain_id=llm_question.domain_id,
                    difficulty=llm_question.difficulty,
                    stem=llm_question.stem,
                    options=[
                        QuestionOption(option_id=option.option_id, text=option.text)
                        for option in llm_question.options
                    ],
                    correct_option_id=llm_question.correct_option_id,
                    explanation=llm_question.explanation,
                )
            )
        elif llm_question.question_type == "multi_answer":
            questions.append(
                MultiAnswerQuestion(
                    question_id=question_id,
                    domain_id=llm_question.domain_id,
                    difficulty=llm_question.difficulty,
                    stem=llm_question.stem,
                    options=[
                        QuestionOption(option_id=option.option_id, text=option.text)
                        for option in llm_question.options
                    ],
                    correct_option_ids=llm_question.correct_option_ids,
                    explanation=llm_question.explanation,
                )
            )
        elif llm_question.question_type == "fill_in_blank":
            questions.append(
                FillInBlankQuestion(
                    question_id=question_id,
                    domain_id=llm_question.domain_id,
                    difficulty=llm_question.difficulty,
                    stem=llm_question.stem,
                    accepted_answers=llm_question.accepted_answers,
                    explanation=llm_question.explanation,
                )
            )
        else:
            questions.append(
                FullTextQuestion(
                    question_id=question_id,
                    domain_id=llm_question.domain_id,
                    difficulty=llm_question.difficulty,
                    stem=llm_question.stem,
                    rubric=llm_question.rubric,
                    explanation=llm_question.explanation,
                )
            )

    return Assessment(
        assessment_id=str(uuid4()),
        syllabus_id=syllabus.syllabus_id,
        topic=syllabus.topic,
        certification=syllabus.certification,
        domains=syllabus.domains,
        questions=questions,
        num_questions=len(questions),
        created_at=datetime.now(timezone.utc),
    )
