from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path(
        "admin/",
        admin.site.urls,
    ),
    path(
        "",
        include("core.urls"),
    ),
    path(
        "courses/",
        include("courses.urls"),
    ),
    path(
        "accounts/",
        include("accounts.urls"),
    ),
    path(
        "management/",
        include("admin_dashboard.urls"),
    ),

    # School support must come before the general school routes.
    path(
        "school/support/",
        include("support.school_urls"),
    ),
    path(
        "school/",
        include("schools.urls"),
    ),

    # Student support.
    path(
        "support/",
        include("support.student_urls"),
    ),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )