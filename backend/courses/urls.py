from django.urls import path

from courses.views import (
    AssessmentCreateView,
    AssessmentRetrieveView,
    GradeAssessmentView,
    RoadmapCreateView,
    SyllabusCreateView,
)

urlpatterns = [
    path("syllabus/", SyllabusCreateView.as_view(), name="syllabus-create"),
    path(
        "syllabus/<str:syllabus_id>/assessment/",
        AssessmentCreateView.as_view(),
        name="assessment-create",
    ),
    path(
        "assessment/<str:assessment_id>/",
        AssessmentRetrieveView.as_view(),
        name="assessment-retrieve",
    ),
    path(
        "assessment/<str:assessment_id>/grade/",
        GradeAssessmentView.as_view(),
        name="assessment-grade",
    ),
    path(
        "assessment/<str:assessment_id>/roadmap/",
        RoadmapCreateView.as_view(),
        name="roadmap-create",
    ),
]
