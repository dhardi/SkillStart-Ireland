from django.urls import path

from . import views


app_name = "admin_dashboard"


urlpatterns = [
    path(
        "",
        views.dashboard,
        name="dashboard",
    ),
    path(
        "courses/",
        views.course_list,
        name="course_list",
    ),

    # Lessons
    path(
        "lessons/",
        views.lesson_list,
        name="lesson_list",
    ),
    path(
        "lessons/add/",
        views.lesson_create,
        name="lesson_create",
    ),
    path(
        "lessons/<int:lesson_id>/edit/",
        views.lesson_update,
        name="lesson_update",
    ),
    path(
        "lessons/<int:lesson_id>/delete/",
        views.lesson_delete,
        name="lesson_delete",
    ),

    path(
        "students/",
        views.student_list,
        name="student_list",
    ),
    path(
        "students/<int:student_id>/",
        views.student_detail,
        name="student_detail",
    ),
    path(
        "enrollments/",
        views.enrollment_list,
        name="enrollment_list",
    ),
    path(
        "enrollments/add/",
        views.enrollment_create,
        name="enrollment_create",
    ),
]