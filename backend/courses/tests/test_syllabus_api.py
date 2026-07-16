import pytest

from courses.models import Syllabus


@pytest.mark.django_db
def test_create_syllabus_persists_and_returns_full_payload(api_client, sample_syllabus, monkeypatch):
    monkeypatch.setattr("courses.views.generate_syllabus", lambda **kwargs: sample_syllabus)

    response = api_client.post(
        "/api/syllabus/",
        {"topic": "Cloud Architecture", "certification": "AWS SAA-C03"},
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["syllabus_id"] == sample_syllabus.syllabus_id
    assert response.json()["domains"][0]["name"] == "Design Resilient Architectures"

    row = Syllabus.objects.get(syllabus_id=sample_syllabus.syllabus_id)
    assert row.topic == "Cloud Architecture"
    assert row.certification == sample_syllabus.certification
    assert row.payload["syllabus_id"] == sample_syllabus.syllabus_id


@pytest.mark.django_db
def test_create_syllabus_requires_topic_and_certification(api_client):
    response = api_client.post("/api/syllabus/", {"topic": "Cloud Architecture"}, format="json")

    assert response.status_code == 400
