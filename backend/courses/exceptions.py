"""Maps llm_engine's typed exceptions to HTTP responses.

Registered as REST_FRAMEWORK["EXCEPTION_HANDLER"] in config/settings.py.
"""

from __future__ import annotations

import logging
from typing import Any

from llm_engine.exceptions import LLMCallError, StructuredOutputError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_exception_handler

logger = logging.getLogger(__name__)


def llm_engine_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    if isinstance(exc, LLMCallError):
        logger.warning("LLM call failed: %s", exc)
        return Response(
            {"error": "llm_call_failed", "detail": str(exc)},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    if isinstance(exc, StructuredOutputError):
        logger.error("LLM output failed schema validation: %s", exc)
        return Response(
            {"error": "llm_output_invalid", "detail": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, ValueError):
        return Response(
            {"error": "invalid_request", "detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return drf_default_exception_handler(exc, context)
