from django.contrib import admin

from courses.models import Assessment, Course, GradedAssessment, Roadmap, Syllabus


@admin.register(Syllabus)
class SyllabusAdmin(admin.ModelAdmin):
    list_display = ("syllabus_id", "owner_id", "topic", "certification", "created_at")
    search_fields = ("topic", "certification", "owner_id")


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("assessment_id", "syllabus", "created_at")


@admin.register(GradedAssessment)
class GradedAssessmentAdmin(admin.ModelAdmin):
    list_display = ("assessment", "graded_at")


@admin.register(Roadmap)
class RoadmapAdmin(admin.ModelAdmin):
    list_display = ("roadmap_id", "assessment", "syllabus", "created_at")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("course_id", "roadmap", "created_at")
