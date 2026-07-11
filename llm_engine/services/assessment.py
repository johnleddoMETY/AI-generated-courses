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
    Question,
    QuestionOption,
    Syllabus,
)

logger = logging.getLogger(__name__)

_EXPECTED_OPTION_IDS = {"A", "B", "C", "D"}


def generate_assessment(
    syllabus: Syllabus,
    num_questions: int = 12,
    exam_date: date | None = None,
) -> Assessment:
    """Generate an MCQ assessment distributed across syllabus domains by weight.

    The per-domain allocation is computed here (largest-remainder method) and
    stated in the prompt; the LLM never does the math. LLM output is
    post-validated in code (4 unique options, correct option present, known
    domain_id) and regenerated with the errors fed back, up to
    MAX_VALIDATION_RETRIES times, before raising StructuredOutputError.
    """
    allocation = _allocate_questions(syllabus.domains, num_questions)
    base_prompt = _build_base_prompt(syllabus, allocation, num_questions, exam_date)

    user_prompt = base_prompt
    errors: list[str] = []
    for attempt in range(1 + MAX_VALIDATION_RETRIES):
        llm_response = structured_completion(
            AssessmentLLMResponse,
            ASSESSMENT_SYSTEM_V1,
            user_prompt,
            task="assessment",
        )
        errors = _post_validate(llm_response, syllabus)
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


def _allocate_questions(domains: list[ExamDomain], num_questions: int) -> dict[str, int]:
    """Distribute num_questions across domains proportional to weight (largest remainder)."""
    total_weight = sum(domain.weight_percent for domain in domains)
    if total_weight <= 0:
        base = num_questions // len(domains)
        counts = {domain.domain_id: base for domain in domains}
        for domain in domains[: num_questions - base * len(domains)]:
            counts[domain.domain_id] += 1
        return counts

    exact = {
        domain.domain_id: num_questions * domain.weight_percent / total_weight
        for domain in domains
    }
    counts = {domain_id: int(value) for domain_id, value in exact.items()}
    shortfall = num_questions - sum(counts.values())
    by_remainder = sorted(exact, key=lambda domain_id: exact[domain_id] - counts[domain_id], reverse=True)
    for domain_id in by_remainder[:shortfall]:
        counts[domain_id] += 1
    return counts


def _build_base_prompt(
    syllabus: Syllabus,
    allocation: dict[str, int],
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
        for domain_id, count in allocation.items()
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
        num_questions=num_questions,
        exam_date_line=exam_date_line,
    )


def _post_validate(llm_response: AssessmentLLMResponse, syllabus: Syllabus) -> list[str]:
    """Check LLM questions against rules strict mode cannot express; return error strings."""
    known_domain_ids = {domain.domain_id for domain in syllabus.domains}
    errors: list[str] = []
    for index, question in enumerate(llm_response.questions, start=1):
        option_ids = [option.option_id for option in question.options]
        if len(question.options) != 4 or set(option_ids) != _EXPECTED_OPTION_IDS:
            errors.append(
                f"Question {index}: must have exactly 4 options with option_ids A, B, C, D "
                f"(got {option_ids})."
            )
        elif question.correct_option_id not in option_ids:
            errors.append(
                f"Question {index}: correct_option_id {question.correct_option_id!r} "
                f"is not among its options."
            )
        if question.domain_id not in known_domain_ids:
            errors.append(
                f"Question {index}: domain_id {question.domain_id!r} is not in the syllabus "
                f"(valid: {sorted(known_domain_ids)})."
            )
    return errors


def _assemble(syllabus: Syllabus, llm_response: AssessmentLLMResponse) -> Assessment:
    """Attach UUIDs and the domain snapshot to validated LLM questions."""
    questions = [
        Question(
            question_id=str(uuid4()),
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
        for llm_question in llm_response.questions
    ]
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
