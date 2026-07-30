import pytest

from courses.models import Assessment, GradedAssessment, Roadmap, Syllabus
from courses.tests.conftest import TEST_USER_ID


def _make_graded_row(sample_syllabus, sample_assessment, sample_graded_assessment):
    syllabus_row = Syllabus.objects.create(
        syllabus_id=sample_syllabus.syllabus_id,
        owner_id=TEST_USER_ID,
        topic=sample_syllabus.topic,
        certification=sample_syllabus.certification,
        exam_code=sample_syllabus.exam_code,
        payload=sample_syllabus.model_dump(mode="json"),
    )
    assessment_row = Assessment.objects.create(
        assessment_id=sample_assessment.assessment_id,
        syllabus=syllabus_row,
        payload=sample_assessment.model_dump(mode="json"),
    )
    GradedAssessment.objects.create(
        assessment=assessment_row,
        payload=sample_graded_assessment.model_dump(mode="json"),
    )
    return syllabus_row, assessment_row


@pytest.mark.django_db
def test_create_roadmap_after_grading(
    api_client, sample_syllabus, sample_assessment, sample_graded_assessment, sample_roadmap, monkeypatch
):
    _make_graded_row(sample_syllabus, sample_assessment, sample_graded_assessment)
    monkeypatch.setattr(
        "courses.views.generate_roadmap", lambda syllabus, graded, **kwargs: sample_roadmap
    )

    response = api_client.post(
        f"/api/assessment/{sample_assessment.assessment_id}/roadmap/", {}, format="json"
    )

    assert response.status_code == 201
    assert response.json()["roadmap_id"] == sample_roadmap.roadmap_id
    assert Roadmap.objects.filter(roadmap_id=sample_roadmap.roadmap_id).exists()


@pytest.mark.django_db
def test_create_roadmap_404_before_grading_exists(api_client, sample_syllabus, sample_assessment):
    syllabus_row = Syllabus.objects.create(
        syllabus_id=sample_syllabus.syllabus_id,
        owner_id=TEST_USER_ID,
        topic=sample_syllabus.topic,
        certification=sample_syllabus.certification,
        exam_code=sample_syllabus.exam_code,
        payload=sample_syllabus.model_dump(mode="json"),
    )
    Assessment.objects.create(
        assessment_id=sample_assessment.assessment_id,
        syllabus=syllabus_row,
        payload=sample_assessment.model_dump(mode="json"),
    )

    response = api_client.post(
        f"/api/assessment/{sample_assessment.assessment_id}/roadmap/", {}, format="json"
    )

    assert response.status_code == 404
