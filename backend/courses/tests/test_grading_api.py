from unittest.mock import MagicMock

import pytest

from courses.models import Assessment, GradedAssessment, Syllabus


def _make_assessment_row(sample_syllabus, sample_assessment):
    syllabus_row = Syllabus.objects.create(
        syllabus_id=sample_syllabus.syllabus_id,
        topic=sample_syllabus.topic,
        certification=sample_syllabus.certification,
        exam_code=sample_syllabus.exam_code,
        payload=sample_syllabus.model_dump(mode="json"),
    )
    return Assessment.objects.create(
        assessment_id=sample_assessment.assessment_id,
        syllabus=syllabus_row,
        payload=sample_assessment.model_dump(mode="json"),
    )


@pytest.mark.django_db
def test_grade_assessment_success(
    api_client, sample_syllabus, sample_assessment, sample_graded_assessment, monkeypatch
):
    _make_assessment_row(sample_syllabus, sample_assessment)
    monkeypatch.setattr(
        "courses.views.grade_assessment", lambda assessment, answers: sample_graded_assessment
    )

    response = api_client.post(
        f"/api/assessment/{sample_assessment.assessment_id}/grade/",
        {"answers": [{"question_id": "33333333-3333-3333-3333-333333333333", "selected_option_id": "A"}]},
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["overall_score_percent"] == 100.0
    assert GradedAssessment.objects.filter(assessment_id=sample_assessment.assessment_id).exists()


@pytest.mark.django_db
def test_grade_assessment_unknown_question_id_returns_400(
    api_client, sample_syllabus, sample_assessment, monkeypatch
):
    _make_assessment_row(sample_syllabus, sample_assessment)

    def _raise(*args, **kwargs):
        raise ValueError("Unknown question_id(s): {'not-a-real-question'}")

    monkeypatch.setattr("courses.views.grade_assessment", _raise)

    response = api_client.post(
        f"/api/assessment/{sample_assessment.assessment_id}/grade/",
        {"answers": [{"question_id": "not-a-real-question", "selected_option_id": "A"}]},
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_grade_uses_server_stored_assessment_not_client_payload(
    api_client, sample_syllabus, sample_assessment, sample_graded_assessment, monkeypatch
):
    """Even if a client sends extra assessment-shaped data, only the stored
    server-side Assessment is ever passed to grade_assessment — matching the
    README's rule to never trust a client-submitted assessment."""
    _make_assessment_row(sample_syllabus, sample_assessment)
    mock_grade = MagicMock(return_value=sample_graded_assessment)
    monkeypatch.setattr("courses.views.grade_assessment", mock_grade)

    api_client.post(
        f"/api/assessment/{sample_assessment.assessment_id}/grade/",
        {
            "answers": [{"question_id": "33333333-3333-3333-3333-333333333333", "selected_option_id": "A"}],
            "questions": [{"question_id": "tampered", "correct_option_id": "D"}],
        },
        format="json",
    )

    called_assessment = mock_grade.call_args.args[0]
    assert called_assessment.assessment_id == sample_assessment.assessment_id
    assert called_assessment.questions[0].correct_option_id == "A"
