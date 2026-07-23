"""Environment-driven configuration for llm_engine.

Settings are read from environment variables at call time (after a
one-time .env load at import), so tests can override them with
monkeypatch.setenv and nothing holds global mutable state.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

TaskName = Literal["syllabus", "assessment", "grading", "roadmap", "lesson"]

DEFAULT_MODEL = "openai/gpt-4o-mini"

#: Extra self-correction rounds after a Pydantic validation failure.
MAX_VALIDATION_RETRIES = 2

_DEFAULT_TEMPERATURES: dict[str, float] = {
    "syllabus": 0.2,
    "assessment": 0.6,
    "grading": 0.2,
    "roadmap": 0.6,
    "lesson": 0.6,
}


@dataclass(frozen=True)
class TaskSettings:
    """Resolved LLM call settings for one pipeline task."""

    model: str
    temperature: float
    timeout: float
    num_retries: int
    fallback_models: list[str]


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw else default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw else default


def get_task_settings(task: TaskName) -> TaskSettings:
    """Resolve model, temperature, timeout, and retry settings for a task.

    Model resolution order: LLM_MODEL_<TASK> env var, then
    LLM_MODEL_DEFAULT, then the built-in default.
    """
    model = (
        os.getenv(f"LLM_MODEL_{task.upper()}")
        or os.getenv("LLM_MODEL_DEFAULT")
        or DEFAULT_MODEL
    )
    fallback_raw = os.getenv("LLM_FALLBACK_MODELS", "")
    return TaskSettings(
        model=model,
        temperature=_env_float(f"LLM_TEMPERATURE_{task.upper()}", _DEFAULT_TEMPERATURES[task]),
        timeout=_env_float("LLM_TIMEOUT_SECONDS", 60.0),
        num_retries=_env_int("LLM_NUM_RETRIES", 2),
        fallback_models=[model.strip() for model in fallback_raw.split(",") if model.strip()],
    )


def get_proficiency_thresholds() -> tuple[float, float]:
    """Return (weak_below, proficient_at) score thresholds in percent.

    score < weak_below -> "weak"; weak_below <= score < proficient_at ->
    "developing"; score >= proficient_at -> "proficient".
    """
    return (
        _env_float("PROFICIENCY_WEAK_BELOW", 50.0),
        _env_float("PROFICIENCY_PROFICIENT_AT", 80.0),
    )
