import pytest

from courses.models import Assessment, Course, GradedAssessment, Roadmap, Syllabus
from courses.tests.conftest import TEST_USER_ID


def _make_roadmap_row(sample_syllabus, sample_assessment, sample_graded_assessment, sample_roadmap):
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
    return Roadmap.objects.create(
        roadmap_id=sample_roadmap.roadmap_id,
        assessment=assessment_row,
        syllabus=syllabus_row,
        payload=sample_roadmap.model_dump(mode="json"),
    )


@pytest.mark.django_db
def test_create_course_from_roadmap(
    api_client,
    sample_syllabus,
    sample_assessment,
    sample_graded_assessment,
    sample_roadmap,
    sample_course,
    monkeypatch,
):
    _make_roadmap_row(sample_syllabus, sample_assessment, sample_graded_assessment, sample_roadmap)
    monkeypatch.setattr("courses.views.generate_course", lambda roadmap: sample_course)

    response = api_client.post(f"/api/roadmap/{sample_roadmap.roadmap_id}/course/", {}, format="json")

    assert response.status_code == 201
    assert response.json()["course_id"] == sample_course.course_id
    assert Course.objects.filter(course_id=sample_course.course_id).exists()


@pytest.mark.django_db
def test_create_course_404_for_unknown_roadmap(api_client):
    response = api_client.post("/api/roadmap/does-not-exist/course/", {}, format="json")

    assert response.status_code == 404


@pytest.mark.django_db
def test_retrieve_course_includes_practice_question_answers(
    api_client,
    sample_syllabus,
    sample_assessment,
    sample_graded_assessment,
    sample_roadmap,
    sample_course,
):
    roadmap_row = _make_roadmap_row(
        sample_syllabus, sample_assessment, sample_graded_assessment, sample_roadmap
    )
    Course.objects.create(
        course_id=sample_course.course_id,
        roadmap=roadmap_row,
        payload=sample_course.model_dump(mode="json"),
    )

    response = api_client.get(f"/api/course/{sample_course.course_id}/")

    assert response.status_code == 200
    # Unlike Assessment, Lesson content is safe to return whole — no stripping.
    assert response.json()["lessons"][0]["practice_questions"][0]["answer"] == "IAM"


@pytest.mark.django_db
def test_retrieve_course_404_for_unknown_id(api_client):
    response = api_client.get("/api/course/does-not-exist/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_regenerate_lesson_replaces_matching_item(
    api_client,
    sample_syllabus,
    sample_assessment,
    sample_graded_assessment,
    sample_roadmap,
    sample_course,
    monkeypatch,
):
    roadmap_row = _make_roadmap_row(
        sample_syllabus, sample_assessment, sample_graded_assessment, sample_roadmap
    )
    Course.objects.create(
        course_id=sample_course.course_id,
        roadmap=roadmap_row,
        payload=sample_course.model_dump(mode="json"),
    )
    item_id = sample_roadmap.items[0].item_id
    new_lesson = sample_course.lessons[0].model_copy(update={"summary": "Refreshed summary."})
    monkeypatch.setattr(
        "courses.views.generate_lesson", lambda item, topic, certification: new_lesson
    )

    response = api_client.post(
        f"/api/course/{sample_course.course_id}/lesson/{item_id}/regenerate/", {}, format="json"
    )

    assert response.status_code == 200
    assert response.json()["summary"] == "Refreshed summary."

    course_row = Course.objects.get(course_id=sample_course.course_id)
    stored_lessons = course_row.payload["lessons"]
    assert len(stored_lessons) == 1
    assert stored_lessons[0]["summary"] == "Refreshed summary."


@pytest.mark.django_db
def test_regenerate_lesson_404_for_unknown_course(api_client):
    response = api_client.post(
        "/api/course/does-not-exist/lesson/some-item/regenerate/", {}, format="json"
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_regenerate_lesson_404_for_item_not_on_roadmap(
    api_client,
    sample_syllabus,
    sample_assessment,
    sample_graded_assessment,
    sample_roadmap,
    sample_course,
):
    roadmap_row = _make_roadmap_row(
        sample_syllabus, sample_assessment, sample_graded_assessment, sample_roadmap
    )
    Course.objects.create(
        course_id=sample_course.course_id,
        roadmap=roadmap_row,
        payload=sample_course.model_dump(mode="json"),
    )

    response = api_client.post(
        f"/api/course/{sample_course.course_id}/lesson/not-a-real-item/regenerate/", {}, format="json"
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_retrieve_course_404_for_a_different_users_course(
    other_user_client,
    sample_syllabus,
    sample_assessment,
    sample_graded_assessment,
    sample_roadmap,
    sample_course,
):
    roadmap_row = _make_roadmap_row(
        sample_syllabus, sample_assessment, sample_graded_assessment, sample_roadmap
    )
    Course.objects.create(
        course_id=sample_course.course_id,
        roadmap=roadmap_row,
        payload=sample_course.model_dump(mode="json"),
    )

    response = other_user_client.get(f"/api/course/{sample_course.course_id}/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_regenerate_lesson_404_for_a_different_users_course(
    other_user_client,
    sample_syllabus,
    sample_assessment,
    sample_graded_assessment,
    sample_roadmap,
    sample_course,
):
    roadmap_row = _make_roadmap_row(
        sample_syllabus, sample_assessment, sample_graded_assessment, sample_roadmap
    )
    Course.objects.create(
        course_id=sample_course.course_id,
        roadmap=roadmap_row,
        payload=sample_course.model_dump(mode="json"),
    )
    item_id = sample_roadmap.items[0].item_id

    response = other_user_client.post(
        f"/api/course/{sample_course.course_id}/lesson/{item_id}/regenerate/", {}, format="json"
    )

    assert response.status_code == 404
