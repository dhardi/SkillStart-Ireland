from django.urls import path

from . import views


app_name = "support"


urlpatterns = [
    path(
        "",
        views.student_ticket_list,
        name="ticket_list",
    ),
    path(
        "new/",
        views.student_ticket_create,
        name="ticket_create",
    ),
    path(
        "attachments/<int:attachment_id>/download/",
        views.student_attachment_download,
        name="attachment_download",
    ),
    path(
        "<str:ticket_number>/",
        views.student_ticket_detail,
        name="ticket_detail",
    ),
]