from typing import Any

import pytest
from pydantic import BaseModel

from llm_engine.client import structured_completion
from llm_engine.exceptions import StructuredOutputError


class DemoResponse(BaseModel):
    """Response model used by client tests."""

    name: str
    score: int


class _Message:
    def __init__(self, content: str | None = None, parsed: Any | None = None) -> None:
        self.content = content
        self.parsed = parsed


class _Choice:
    def __init__(self, message: _Message) -> None:
        self.message = message


class _Response:
    def __init__(self, message: _Message) -> None:
        self.choices = [_Choice(message)]
        self.usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}


def test_native_parsed_model_passes_through(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_completion(**kwargs: Any) -> _Response:
        assert kwargs["response_format"] is DemoResponse
        assert kwargs["messages"][0]["role"] == "system"
        return _Response(_Message(parsed=DemoResponse(name="Ada", score=10)))

    monkeypatch.setattr("llm_engine.client.litellm.completion", fake_completion)
    monkeypatch.setattr("llm_engine.client.litellm.completion_cost", lambda response: 0.01)

    result = structured_completion(DemoResponse, "system", "user", task="syllabus")

    assert result == DemoResponse(name="Ada", score=10)


def test_json_content_is_validated(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_completion(**kwargs: Any) -> _Response:
        return _Response(_Message(content='{"name": "Ada", "score": 10}'))

    monkeypatch.setattr("llm_engine.client.litellm.completion", fake_completion)
    monkeypatch.setattr("llm_engine.client.litellm.completion_cost", lambda response: 0.01)

    result = structured_completion(DemoResponse, "system", "user", task="grading")

    assert result == DemoResponse(name="Ada", score=10)


def test_validation_error_retries_with_error_fed_back(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[dict[str, str]]] = []

    def fake_completion(**kwargs: Any) -> _Response:
        calls.append(kwargs["messages"])
        if len(calls) == 1:
            return _Response(_Message(content='{"name": "Ada", "score": "bad"}'))
        return _Response(_Message(content='{"name": "Ada", "score": 10}'))

    monkeypatch.setattr("llm_engine.client.litellm.completion", fake_completion)
    monkeypatch.setattr("llm_engine.client.litellm.completion_cost", lambda response: 0.02)

    result = structured_completion(DemoResponse, "system", "user", task="assessment")

    assert result.score == 10
    assert len(calls) == 2
    retry_messages = calls[1]
    assert retry_messages[-2]["role"] == "assistant"
    assert retry_messages[-1]["role"] == "user"
    assert "Validation failed" in retry_messages[-1]["content"]


def test_exhausted_validation_retries_raise_structured_output_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_count = 0

    def fake_completion(**kwargs: Any) -> _Response:
        nonlocal call_count
        call_count += 1
        return _Response(_Message(content='{"name": "Ada", "score": "bad"}'))

    monkeypatch.setattr("llm_engine.client.litellm.completion", fake_completion)
    monkeypatch.setattr("llm_engine.client.litellm.completion_cost", lambda response: 0.03)

    with pytest.raises(StructuredOutputError):
        structured_completion(DemoResponse, "system", "user", task="roadmap")

    assert call_count == 3  # 1 initial + MAX_VALIDATION_RETRIES


def test_native_rejection_falls_back_to_json_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_completion(**kwargs: Any) -> _Response:
        calls.append(kwargs)
        if "response_format" in kwargs:
            raise RuntimeError("provider does not support response_format")
        return _Response(_Message(content='{"name": "Ada", "score": 10}'))

    monkeypatch.setattr("llm_engine.client.litellm.completion", fake_completion)
    monkeypatch.setattr("llm_engine.client.litellm.completion_cost", lambda response: 0.01)

    result = structured_completion(DemoResponse, "system", "user", task="syllabus")

    assert result.score == 10
    assert len(calls) == 2
    json_mode_system = calls[1]["messages"][0]["content"]
    assert "JSON" in json_mode_system
