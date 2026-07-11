"""Typed exceptions raised by llm_engine.

Every failure surfaces as one of these; nothing returns None silently.
"""


class LLMEngineError(Exception):
    """Base class for all llm_engine errors."""


class LLMCallError(LLMEngineError):
    """The LLM call itself failed (network, auth, provider error) after retries."""


class StructuredOutputError(LLMEngineError):
    """The LLM response never validated against the expected schema after retries."""
