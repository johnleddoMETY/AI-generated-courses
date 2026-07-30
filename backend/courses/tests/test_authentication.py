import pytest


@pytest.mark.django_db
def test_request_without_token_is_rejected(anonymous_client):
    response = anonymous_client.post(
        "/api/syllabus/", {"topic": "Cloud", "certification": "SAA-C03"}, format="json"
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_request_with_garbage_token_is_rejected(anonymous_client):
    anonymous_client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")

    response = anonymous_client.post(
        "/api/syllabus/", {"topic": "Cloud", "certification": "SAA-C03"}, format="json"
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_request_with_valid_token_passes_the_gate(api_client, monkeypatch, sample_syllabus):
    # A valid token should reach the view — 400 here (missing fields) still
    # proves auth passed, since a 401 would have short-circuited first.
    monkeypatch.setattr("courses.views.generate_syllabus", lambda **kwargs: sample_syllabus)

    response = api_client.post("/api/syllabus/", {}, format="json")

    assert response.status_code == 400
