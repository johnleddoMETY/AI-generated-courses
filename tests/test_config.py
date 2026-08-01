import pytest

from llm_engine.config import get_proficiency_thresholds, get_task_settings


def test_task_settings_defaults() -> None:
    settings = get_task_settings("syllabus")
    assert settings.model == "openai/gpt-4o-mini"
    assert settings.temperature == 0.2
    assert settings.timeout == 60.0
    assert settings.num_retries == 2
    assert settings.fallback_models == []

    assert get_task_settings("assessment").temperature == 0.6
    assert get_task_settings("grading").temperature == 0.2
    assert get_task_settings("roadmap").temperature == 0.6
    assert get_task_settings("lesson").temperature == 0.6


def test_task_settings_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MODEL_DEFAULT", "openai/gpt-4o")
    monkeypatch.setenv("LLM_MODEL_ROADMAP", "openrouter/anthropic/claude-sonnet-4-5")
    monkeypatch.setenv("LLM_TEMPERATURE_ROADMAP", "0.3")
    monkeypatch.setenv("LLM_FALLBACK_MODELS", "openai/gpt-4o, openai/gpt-4o-mini")

    roadmap = get_task_settings("roadmap")
    assert roadmap.model == "openrouter/anthropic/claude-sonnet-4-5"
    assert roadmap.temperature == 0.3
    assert roadmap.fallback_models == ["openai/gpt-4o", "openai/gpt-4o-mini"]

    assert get_task_settings("grading").model == "openai/gpt-4o"


def test_proficiency_thresholds(monkeypatch: pytest.MonkeyPatch) -> None:
    assert get_proficiency_thresholds() == (50.0, 80.0)
    monkeypatch.setenv("PROFICIENCY_WEAK_BELOW", "40")
    monkeypatch.setenv("PROFICIENCY_PROFICIENT_AT", "85")
    assert get_proficiency_thresholds() == (40.0, 85.0)
