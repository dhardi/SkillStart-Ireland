from django.urls import path

from . import views


app_name = "school_support"


urlpatterns = [
    path(
        "",
        views.school_ticket_list,
        name="ticket_list",
    ),
    path(
        "new/",
        views.school_ticket_create,
        name="ticket_create",
    ),
    path(
        "attachments/<int:attachment_id>/download/",
        views.school_attachment_download,
        name="attachment_download",
    ),
    path(
        "<str:ticket_number>/",
        views.school_ticket_detail,
        name="ticket_detail",
    ),
]