import json

import pytest

from courses.models import Assessment, Syllabus
from courses.tests.conftest import TEST_USER_ID

_SECRET_FIELDS = ("correct_option_id", "explanation")


def _make_syllabus_row(sample_syllabus):
    return Syllabus.objects.create(
        syllabus_id=sample_syllabus.syllabus_id,
        owner_id=TEST_USER_ID,
        topic=sample_syllabus.topic,
        certification=sample_syllabus.certification,
        exam_code=sample_syllabus.exam_code,
        payload=sample_syllabus.model_dump(mode="json"),
    )


@pytest.mark.django_db
def test_create_assessment_strips_answer_key_from_response(
    api_client, sample_syllabus, sample_assessment, monkeypatch
):
    _make_syllabus_row(sample_syllabus)
    monkeypatch.setattr(
        "courses.views.generate_assessment", lambda syllabus, **kwargs: sample_assessment
    )

    response = api_client.post(
        f"/api/syllabus/{sample_syllabus.syllabus_id}/assessment/",
        {"num_questions": 1},
        format="json",
    )

    assert response.status_code == 201
    body_text = json.dumps(response.json())
    for field in _SECRET_FIELDS:
        assert field not in body_text, f"{field} leaked into the public assessment response"

    # But the server-side stored row must keep the full answer key.
    row = Assessment.objects.get(assessment_id=sample_assessment.assessment_id)
    assert row.payload["questions"][0]["correct_option_id"] == "A"
    assert row.payload["questions"][0]["explanation"]


@pytest.mark.django_db
def test_create_assessment_strips_answer_key_for_every_question_type(
    api_client, sample_syllabus, sample_assessment_all_types, monkeypatch
):
    """multi_answer/fill_in_blank/full_text each reveal the answer through a
    different field (correct_option_ids/accepted_answers/rubric) — none of
    them should leak, same as correct_option_id for single_answer."""
    _make_syllabus_row(sample_syllabus)
    monkeypatch.setattr(
        "courses.views.generate_assessment", lambda syllabus, **kwargs: sample_assessment_all_types
    )

    response = api_client.post(
        f"/api/syllabus/{sample_syllabus.syllabus_id}/assessment/",
        {"num_questions": 4},
        format="json",
    )

    assert response.status_code == 201
    body_text = json.dumps(response.json())
    for field in ("correct_option_id", "correct_option_ids", "accepted_answers", "rubric", "explanation"):
        assert field not in body_text, f"{field} leaked into the public assessment response"

    # But the server-side stored row must keep every answer key intact.
    row = Assessment.objects.get(assessment_id=sample_assessment_all_types.assessment_id)
    by_id = {q["question_id"]: q for q in row.payload["questions"]}
    assert by_id["q-single"]["correct_option_id"] == "A"
    assert by_id["q-multi"]["correct_option_ids"] == ["A", "B"]
    assert by_id["q-fill"]["accepted_answers"] == ["IAM"]
    assert by_id["q-text"]["rubric"]


@pytest.mark.django_db
def test_create_assessment_404_for_unknown_syllabus(api_client):
    response = api_client.post(
        "/api/syllabus/does-not-exist/assessment/", {"num_questions": 1}, format="json"
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_retrieve_assessment_strips_answer_key(api_client, sample_syllabus, sample_assessment):
    syllabus_row = _make_syllabus_row(sample_syllabus)
    Assessment.objects.create(
        assessment_id=sample_assessment.assessment_id,
        syllabus=syllabus_row,
        payload=sample_assessment.model_dump(mode="json"),
    )

    response = api_client.get(f"/api/assessment/{sample_assessment.assessment_id}/")

    assert response.status_code == 200
    body_text = json.dumps(response.json())
    for field in _SECRET_FIELDS:
        assert field not in body_text


@pytest.mark.django_db
def test_retrieve_assessment_404_for_a_different_users_assessment(
    other_user_client, sample_syllabus, sample_assessment
):
    syllabus_row = _make_syllabus_row(sample_syllabus)
    Assessment.objects.create(
        assessment_id=sample_assessment.assessment_id,
        syllabus=syllabus_row,
        payload=sample_assessment.model_dump(mode="json"),
    )

    response = other_user_client.get(f"/api/assessment/{sample_assessment.assessment_id}/")

    assert response.status_code == 404
