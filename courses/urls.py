from django.urls import path

from . import views


app_name = "courses"


urlpatterns = [
    path(
        "",
        views.course_list,
        name="course_list",
    ),
    path(
        "<slug:slug>/",
        views.course_detail,
        name="course_detail",
    ),
    path(
        "<slug:course_slug>/lessons/<int:lesson_id>/",
        views.lesson_detail,
        name="lesson_detail",
    ),
    path(
        (
            "<slug:course_slug>/lessons/"
            "<int:lesson_id>/complete/"
        ),
        views.mark_lesson_completed,
        name="mark_lesson_completed",
    ),
    path(
        "<slug:course_slug>/assessment/",
        views.assessment_detail,
        name="assessment_detail",
    ),
    path(
        "<slug:course_slug>/assessment/start/",
        views.start_assessment,
        name="start_assessment",
    ),
    path(
        (
            "<slug:course_slug>/assessment/"
            "attempt/<int:attempt_id>/"
            "question/<int:position>/"
        ),
        views.assessment_attempt,
        name="assessment_attempt",
    ),
    path(
    (
        "<slug:course_slug>/assessment/"
        "attempt/<int:attempt_id>/result/"
    ),
    views.assessment_result,
    name="assessment_result",
),
]