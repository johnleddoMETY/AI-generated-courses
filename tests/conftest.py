import pytest

_LLM_ENV_VARS = [
    "LLM_MODEL_DEFAULT",
    "LLM_MODEL_SYLLABUS",
    "LLM_MODEL_ASSESSMENT",
    "LLM_MODEL_GRADING",
    "LLM_MODEL_ROADMAP",
    "LLM_FALLBACK_MODELS",
    "LLM_TEMPERATURE_SYLLABUS",
    "LLM_TEMPERATURE_ASSESSMENT",
    "LLM_TEMPERATURE_GRADING",
    "LLM_TEMPERATURE_ROADMAP",
    "LLM_TIMEOUT_SECONDS",
    "LLM_NUM_RETRIES",
    "PROFICIENCY_WEAK_BELOW",
    "PROFICIENCY_PROFICIENT_AT",
]


@pytest.fixture(autouse=True)
def _clean_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate tests from the developer's real .env / exported LLM_* vars."""
    for name in _LLM_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
