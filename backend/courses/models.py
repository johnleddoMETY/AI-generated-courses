"""Persistence for the llm_engine pipeline.

Each row stores the full model_dump(mode="json") of the corresponding
llm_engine Pydantic object in `payload`, keyed on the same UUID string
the object already carries (llm_engine generates these in code, so
they're safe primary keys — see README's "Integration rules"). A few
columns are pulled out of payload for querying/joins; everything else
stays in the JSON blob and is reconstructed via Model.model_validate()
before being handed back into llm_engine service functions.
"""

from __future__ import annotations

from django.db import models


class Syllabus(models.Model):
    """owner_id is the Supabase user id (JWT 'sub' claim) that created this
    syllabus. It's the root of the ownership chain — every downstream model
    (Assessment, Roadmap, Course, ...) is scoped by following FKs back here,
    rather than each carrying its own owner_id.
    """

    syllabus_id = models.CharField(primary_key=True, max_length=36)
    owner_id = models.CharField(max_length=36)
    topic = models.CharField(max_length=255)
    certification = models.CharField(max_length=255)
    exam_code = models.CharField(max_length=50, null=True, blank=True)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.certification} ({self.syllabus_id})"


class Assessment(models.Model):
    """payload includes correct_option_id/explanation per question.

    SECURITY: never return this row's payload directly to a client —
    always go through courses.serializers.serialize_assessment_public.
    """

    assessment_id = models.CharField(primary_key=True, max_length=36)
    syllabus = models.ForeignKey(
        Syllabus, on_delete=models.CASCADE, to_field="syllabus_id", related_name="assessments"
    )
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Assessment {self.assessment_id}"


class GradedAssessment(models.Model):
    assessment = models.OneToOneField(
        Assessment,
        on_delete=models.CASCADE,
        to_field="assessment_id",
        primary_key=True,
        related_name="graded_assessment",
    )
    payload = models.JSONField()
    graded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"GradedAssessment {self.assessment_id}"


class Roadmap(models.Model):
    roadmap_id = models.CharField(primary_key=True, max_length=36)
    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, to_field="assessment_id", related_name="roadmaps"
    )
    syllabus = models.ForeignKey(
        Syllabus, on_delete=models.CASCADE, to_field="syllabus_id", related_name="roadmaps"
    )
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Roadmap {self.roadmap_id}"


class Course(models.Model):
    """No security stripping needed: unlike Assessment, Lesson content
    (including practice_questions) is meant to be shown to the client
    whole — nothing here is scored.
    """

    course_id = models.CharField(primary_key=True, max_length=36)
    roadmap = models.ForeignKey(
        Roadmap, on_delete=models.CASCADE, to_field="roadmap_id", related_name="courses"
    )
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Course {self.course_id}"
