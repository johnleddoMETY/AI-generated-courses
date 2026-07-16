"""HTTP views for the 4-stage llm_engine pipeline.

Each view's job is persistence + HTTP shaping only — pipeline logic
(allocation math, grading, gap-targeting) stays inside llm_engine. Views
reconstruct llm_engine Pydantic objects from stored JSON via
Model.model_validate() before calling into the service functions.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from llm_engine import (
    Assessment as AssessmentModel,
)
from llm_engine import (
    GradedAssessment as GradedAssessmentModel,
)
from llm_engine import (
    Syllabus as SyllabusModel,
)
from llm_engine import (
    UserAnswer,
    generate_assessment,
    generate_roadmap,
    generate_syllabus,
    grade_assessment,
)
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from courses.models import Assessment, GradedAssessment, Roadmap, Syllabus
from courses.serializers import (
    AssessmentCreateRequestSerializer,
    GradeRequestSerializer,
    RoadmapCreateRequestSerializer,
    SyllabusCreateRequestSerializer,
    serialize_assessment_public,
)


class SyllabusCreateView(APIView):
    def post(self, request: Request) -> Response:
        body = SyllabusCreateRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)

        syllabus = generate_syllabus(**body.validated_data)

        payload = syllabus.model_dump(mode="json")
        Syllabus.objects.create(
            syllabus_id=syllabus.syllabus_id,
            topic=syllabus.topic,
            certification=syllabus.certification,
            exam_code=syllabus.exam_code,
            payload=payload,
        )
        return Response(payload, status=status.HTTP_201_CREATED)


class AssessmentCreateView(APIView):
    def post(self, request: Request, syllabus_id: str) -> Response:
        body = AssessmentCreateRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)

        syllabus_row = get_object_or_404(Syllabus, syllabus_id=syllabus_id)
        syllabus = SyllabusModel.model_validate(syllabus_row.payload)

        assessment = generate_assessment(syllabus, **body.validated_data)

        payload = assessment.model_dump(mode="json")
        Assessment.objects.create(
            assessment_id=assessment.assessment_id,
            syllabus=syllabus_row,
            payload=payload,
        )
        return Response(serialize_assessment_public(payload), status=status.HTTP_201_CREATED)


class AssessmentRetrieveView(APIView):
    def get(self, request: Request, assessment_id: str) -> Response:
        assessment_row = get_object_or_404(Assessment, assessment_id=assessment_id)
        return Response(serialize_assessment_public(assessment_row.payload))


class GradeAssessmentView(APIView):
    def post(self, request: Request, assessment_id: str) -> Response:
        body = GradeRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)

        # Always grade against the server-stored assessment — never trust
        # anything about questions/answer-key that the client might send.
        assessment_row = get_object_or_404(Assessment, assessment_id=assessment_id)
        assessment = AssessmentModel.model_validate(assessment_row.payload)
        answers = [UserAnswer(**answer) for answer in body.validated_data["answers"]]

        graded = grade_assessment(assessment, answers)

        payload = graded.model_dump(mode="json")
        GradedAssessment.objects.update_or_create(
            assessment=assessment_row, defaults={"payload": payload}
        )
        return Response(payload, status=status.HTTP_201_CREATED)


class RoadmapCreateView(APIView):
    def post(self, request: Request, assessment_id: str) -> Response:
        body = RoadmapCreateRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)

        assessment_row = get_object_or_404(Assessment, assessment_id=assessment_id)
        graded_row = get_object_or_404(GradedAssessment, assessment=assessment_row)
        syllabus_row = assessment_row.syllabus

        syllabus = SyllabusModel.model_validate(syllabus_row.payload)
        graded = GradedAssessmentModel.model_validate(graded_row.payload)

        roadmap = generate_roadmap(syllabus, graded, **body.validated_data)

        payload = roadmap.model_dump(mode="json")
        Roadmap.objects.create(
            roadmap_id=roadmap.roadmap_id,
            assessment=assessment_row,
            syllabus=syllabus_row,
            payload=payload,
        )
        return Response(payload, status=status.HTTP_201_CREATED)
