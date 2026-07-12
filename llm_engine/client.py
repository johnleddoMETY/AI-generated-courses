"""LiteLLM wrapper providing schema-validated completions.

Every LLM interaction in llm_engine goes through structured_completion.
This is the ONLY place LLM text is parsed, and the only parsing is
Pydantic's model_validate_json on the validated fallback path.
"""

from __future__ import annotations

import json
import logging
from typing import Any, TypeVar

import litellm
from pydantic import BaseModel, ValidationError

from llm_engine.config import MAX_VALIDATION_RETRIES, TaskName, TaskSettings, get_task_settings
from llm_engine.exceptions import LLMCallError, StructuredOutputError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_JSON_MODE_INSTRUCTION = (
    "\n\nRespond with a single JSON object that conforms exactly to the JSON "
    "schema below. Output only the JSON object — no prose, no code fences.\n\n"
    "JSON schema:\n{schema}"
)


def structured_completion(
    response_model: type[T],
    system_prompt: str,
    user_prompt: str,
    *,
    task: TaskName,
) -> T:
    """Call the configured LLM and return a validated response_model instance.

    Resolves model + temperature from config by task. Tries LiteLLM native
    structured output (response_format=response_model) first; if the
    provider rejects that call, falls back to a JSON-mode instruction plus
    manual validation. Pydantic validation failures are fed back to the
    model for up to MAX_VALIDATION_RETRIES self-correction rounds, then
    raise StructuredOutputError. Call failures raise LLMCallError.
    """
    settings = get_task_settings(task)
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    use_native = True
    last_error = ""

    for attempt in range(1 + MAX_VALIDATION_RETRIES):
        response, use_native = _call_llm(
            response_model, messages, settings, task=task, use_native=use_native
        )
        _log_usage(response, task=task, model=settings.model)

        message = response.choices[0].message
        parsed = getattr(message, "parsed", None)
        if isinstance(parsed, response_model):
            return parsed

        content = message.content or ""
        try:
            return response_model.model_validate_json(content)
        except ValidationError as exc:
            last_error = str(exc)
            logger.warning(
                "Validation failed for task=%s attempt=%d/%d",
                task,
                attempt + 1,
                1 + MAX_VALIDATION_RETRIES,
            )
            logger.debug("Invalid payload for task=%s: %s", task, content)
            messages.append({"role": "assistant", "content": content})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"Validation failed with the following errors:\n{last_error}\n\n"
                        "Return a corrected JSON object that fixes every error and "
                        "conforms exactly to the required schema."
                    ),
                }
            )

    raise StructuredOutputError(
        f"LLM output for task '{task}' failed schema validation after "
        f"{1 + MAX_VALIDATION_RETRIES} attempts. Last error:\n{last_error}"
    )


def _call_llm(
    response_model: type[T],
    messages: list[dict[str, str]],
    settings: TaskSettings,
    *,
    task: TaskName,
    use_native: bool,
) -> tuple[Any, bool]:
    """Make one LiteLLM call; returns (response, native_mode_still_usable)."""
    kwargs: dict[str, Any] = {
        "model": settings.model,
        "messages": messages,
        "temperature": settings.temperature,
        "timeout": settings.timeout,
        "num_retries": settings.num_retries,
    }
    if settings.fallback_models:
        kwargs["fallbacks"] = settings.fallback_models

    if use_native:
        try:
            return litellm.completion(**kwargs, response_format=response_model), True
        except Exception as exc:  # noqa: BLE001 — any provider rejection triggers fallback
            logger.warning(
                "Native structured output failed for task=%s (%s); "
                "falling back to JSON mode",
                task,
                exc,
            )

    schema = json.dumps(response_model.model_json_schema(), indent=2)
    json_messages = [
        {
            "role": "system",
            "content": messages[0]["content"] + _JSON_MODE_INSTRUCTION.format(schema=schema),
        },
        *messages[1:],
    ]
    try:
        return litellm.completion(**{**kwargs, "messages": json_messages}), False
    except Exception as exc:
        raise LLMCallError(f"LLM call failed for task '{task}': {exc}") from exc


def _log_usage(response: Any, *, task: TaskName, model: str) -> None:
    """Log token usage and cost for one call at INFO level."""
    usage = getattr(response, "usage", None)
    if isinstance(usage, dict):
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
    else:
        prompt_tokens = getattr(usage, "prompt_tokens", None)
        completion_tokens = getattr(usage, "completion_tokens", None)
    try:
        cost: float | None = litellm.completion_cost(response)
    except Exception:  # noqa: BLE001 — cost lookup can fail for unknown models
        cost = None
    logger.info(
        "llm call task=%s model=%s prompt_tokens=%s completion_tokens=%s cost_usd=%s",
        task,
        model,
        prompt_tokens,
        completion_tokens,
        f"{cost:.6f}" if cost is not None else "unknown",
    )
