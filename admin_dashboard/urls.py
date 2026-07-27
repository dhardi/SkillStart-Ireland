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