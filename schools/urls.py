from django.urls import path

from . import views


app_name = "schools"


urlpatterns = [
    path(
        "",
        views.dashboard,
        name="dashboard",
    ),
    path(
        "students/",
        views.student_list,
        name="student_list",
    ),
    path(
        "students/add/",
        views.student_create,
        name="student_create",
    ),
    path(
        "students/<int:student_id>/",
        views.student_detail,
        name="student_detail",
    ),
    path(
        "students/<int:student_id>/edit/",
        views.student_update,
        name="student_update",
    ),
    path(
        "students/<int:student_id>/deactivate/",
        views.student_deactivate,
        name="student_deactivate",
    ),
    path(
        "students/<int:student_id>/reactivate/",
        views.student_reactivate,
        name="student_reactivate",
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
    path(
        "certificates/",
        views.certificate_list,
        name="certificate_list",
    ),
    path(
        "certificates/<str:certificate_number>/pdf/",
        views.certificate_pdf,
        name="certificate_pdf",
    ),
]
