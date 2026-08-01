"""Request validation and response shaping for the courses API.

Response payloads are already valid JSON (llm_engine models are dumped
via model_dump(mode="json") before being stored), so "serializing" a
response is mostly picking which stored payload to return as-is. The
one exception is serialize_assessment_public, which enforces the
README's security rule: the answer key must never reach the frontend.
"""

from __future__ import annotations

import copy
from typing import Any

from rest_framework import serializers

OptionID = ("A", "B", "C", "D")


def serialize_assessment_public(payload: dict[str, Any]) -> dict[str, Any]:
    """Return an assessment payload with correct_option_id/explanation stripped from every question."""
    stripped = copy.deepcopy(payload)
    for question in stripped.get("questions", []):
        question.pop("correct_option_id", None)
        question.pop("explanation", None)
    return stripped


class SyllabusCreateRequestSerializer(serializers.Serializer):
    topic = serializers.CharField(max_length=255)
    certification = serializers.CharField(max_length=255)


class AssessmentCreateRequestSerializer(serializers.Serializer):
    num_questions = serializers.IntegerField(default=12, min_value=1, max_value=100)
    exam_date = serializers.DateField(required=False, allow_null=True, default=None)


class UserAnswerRequestSerializer(serializers.Serializer):
    question_id = serializers.CharField()
    selected_option_id = serializers.ChoiceField(choices=OptionID, allow_null=True)


class GradeRequestSerializer(serializers.Serializer):
    answers = UserAnswerRequestSerializer(many=True)


class RoadmapCreateRequestSerializer(serializers.Serializer):
    exam_date = serializers.DateField(required=False, allow_null=True, default=None)
