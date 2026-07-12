"""Syllabus generation: one LLM call producing the exam blueprint."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from uuid import uuid4

from llm_engine.client import structured_completion
from llm_engine.prompts.syllabus_prompts import SYLLABUS_SYSTEM_V1, build_syllabus_user_prompt
from llm_engine.schemas import ExamDomain, Syllabus, SyllabusLLMResponse

logger = logging.getLogger(__name__)


def generate_syllabus(topic: str, certification: str) -> Syllabus:
    """Generate the exam blueprint (domains, weights, key topics) for a certification.

    Uses the real blueprint when the certification is well-known; otherwise a
    generic breakdown flagged in source_note. Slug domain_ids and the UUID
    syllabus_id are assigned here, never by the LLM.
    """
    llm_response = structured_completion(
        SyllabusLLMResponse,
        SYLLABUS_SYSTEM_V1,
        build_syllabus_user_prompt(topic, certification),
        task="syllabus",
    )

    domains: list[ExamDomain] = []
    seen_slugs: set[str] = set()
    for llm_domain in llm_response.domains:
        slug = _unique_slug(_slugify(llm_domain.name), seen_slugs)
        seen_slugs.add(slug)
        domains.append(
            ExamDomain(
                domain_id=slug,
                name=llm_domain.name,
                weight_percent=llm_domain.weight_percent,
                key_topics=llm_domain.key_topics,
            )
        )

    total_weight = sum(domain.weight_percent for domain in domains)
    if not 90.0 <= total_weight <= 110.0:
        logger.warning(
            "Syllabus domain weights sum to %.1f (expected ~100) for certification=%r",
            total_weight,
            certification,
        )

    return Syllabus(
        syllabus_id=str(uuid4()),
        topic=topic,
        certification=certification,
        exam_code=llm_response.exam_code,
        domains=domains,
        source_note=llm_response.source_note,
        created_at=datetime.now(timezone.utc),
    )


def _slugify(name: str) -> str:
    """Turn a domain name into a short lowercase slug ('Design Secure...' -> 'design-secure-...')."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "domain"


def _unique_slug(slug: str, seen: set[str]) -> str:
    """Suffix the slug with -2, -3, ... until it is unique within this syllabus."""
    if slug not in seen:
        return slug
    counter = 2
    while f"{slug}-{counter}" in seen:
        counter += 1
    return f"{slug}-{counter}"
