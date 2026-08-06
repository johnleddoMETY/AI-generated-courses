from django.urls import path

from courses.views import (
    AssessmentCreateView,
    AssessmentRetrieveView,
    CourseCreateView,
    CourseRetrieveView,
    GradeAssessmentView,
    LessonRegenerateView,
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
    path(
        "roadmap/<str:roadmap_id>/course/",
        CourseCreateView.as_view(),
        name="course-create",
    ),
    path(
        "course/<str:course_id>/",
        CourseRetrieveView.as_view(),
        name="course-retrieve",
    ),
    path(
        "course/<str:course_id>/lesson/<str:item_id>/regenerate/",
        LessonRegenerateView.as_view(),
        name="lesson-regenerate",
    ),
]
