"""Versioned prompt constants and prompt-builder functions."""

from llm_engine.prompts.assessment_prompts import (
    ASSESSMENT_RETRY_SUFFIX_V1,
    ASSESSMENT_SYSTEM_V1,
    ASSESSMENT_USER_TEMPLATE_V1,
)
from llm_engine.prompts.grading_prompts import GRADING_SYSTEM_V1, GRADING_USER_TEMPLATE_V1
from llm_engine.prompts.roadmap_prompts import ROADMAP_SYSTEM_V1, ROADMAP_USER_TEMPLATE_V1
from llm_engine.prompts.syllabus_prompts import SYLLABUS_SYSTEM_V1, SYLLABUS_USER_TEMPLATE_V1

__all__ = [
    "ASSESSMENT_RETRY_SUFFIX_V1",
    "ASSESSMENT_SYSTEM_V1",
    "ASSESSMENT_USER_TEMPLATE_V1",
    "GRADING_SYSTEM_V1",
    "GRADING_USER_TEMPLATE_V1",
    "ROADMAP_SYSTEM_V1",
    "ROADMAP_USER_TEMPLATE_V1",
    "SYLLABUS_SYSTEM_V1",
    "SYLLABUS_USER_TEMPLATE_V1",
]
