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
]