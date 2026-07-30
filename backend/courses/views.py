"""HTTP views for the 5-stage llm_engine pipeline.

Each view's job is persistence + HTTP shaping only — pipeline logic
(allocation math, grading, gap-targeting) stays inside llm_engine. Views
reconstruct llm_engine Pydantic objects from stored JSON via
Model.model_validate() before calling into the service functions.
"""

from __future__ import annotations

from django.http import Http404
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
    Roadmap as RoadmapModel,
)
from llm_engine import (
    UserAnswer,
    generate_assessment,
    generate_course,
    generate_lesson,
    generate_roadmap,
    generate_syllabus,
    grade_assessment,
)
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from courses.models import Assessment, Course, GradedAssessment, Roadmap, Syllabus
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
            owner_id=request.user.id,
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

        syllabus_row = get_object_or_404(Syllabus, syllabus_id=syllabus_id, owner_id=request.user.id)
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
        assessment_row = get_object_or_404(
            Assessment, assessment_id=assessment_id, syllabus__owner_id=request.user.id
        )
        return Response(serialize_assessment_public(assessment_row.payload))


class GradeAssessmentView(APIView):
    def post(self, request: Request, assessment_id: str) -> Response:
        body = GradeRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)

        # Always grade against the server-stored assessment — never trust
        # anything about questions/answer-key that the client might send.
        assessment_row = get_object_or_404(
            Assessment, assessment_id=assessment_id, syllabus__owner_id=request.user.id
        )
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

        assessment_row = get_object_or_404(
            Assessment, assessment_id=assessment_id, syllabus__owner_id=request.user.id
        )
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


class CourseCreateView(APIView):
    """Generates one lesson per roadmap item, sequentially, one LLM call each.

    NOTE: this runs synchronously inside the request like the other four
    endpoints, but it is far slower (README: "treat it as a background
    job, not something to run inside a request/response cycle"). Fine for
    now; swap to a background task queue before this is client-facing.
    """

    def post(self, request: Request, roadmap_id: str) -> Response:
        roadmap_row = get_object_or_404(
            Roadmap, roadmap_id=roadmap_id, syllabus__owner_id=request.user.id
        )
        roadmap = RoadmapModel.model_validate(roadmap_row.payload)

        course = generate_course(roadmap)

        payload = course.model_dump(mode="json")
        Course.objects.create(
            course_id=course.course_id,
            roadmap=roadmap_row,
            payload=payload,
        )
        return Response(payload, status=status.HTTP_201_CREATED)


class CourseRetrieveView(APIView):
    def get(self, request: Request, course_id: str) -> Response:
        course_row = get_object_or_404(
            Course, course_id=course_id, roadmap__syllabus__owner_id=request.user.id
        )
        return Response(course_row.payload)


class LessonRegenerateView(APIView):
    """Regenerates one lesson and swaps it into the stored Course.

    For refreshing stale content or retrying a single lesson that came out
    bad, without paying for a full course regeneration.
    """

    def post(self, request: Request, course_id: str, item_id: str) -> Response:
        course_row = get_object_or_404(
            Course, course_id=course_id, roadmap__syllabus__owner_id=request.user.id
        )
        roadmap = RoadmapModel.model_validate(course_row.roadmap.payload)

        item = next((i for i in roadmap.items if i.item_id == item_id), None)
        if item is None:
            raise Http404(f"No roadmap item '{item_id}' on this course's roadmap.")

        lesson = generate_lesson(item, roadmap.topic, roadmap.certification)
        lesson_payload = lesson.model_dump(mode="json")

        lessons = course_row.payload["lessons"]
        index = next((i for i, existing in enumerate(lessons) if existing["item_id"] == item_id), None)
        if index is None:
            lessons.append(lesson_payload)
        else:
            lessons[index] = lesson_payload

        course_row.save(update_fields=["payload"])
        return Response(lesson_payload, status=status.HTTP_200_OK)
