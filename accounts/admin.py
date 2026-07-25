from django.contrib import admin

from .models import Enrollment


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "course",
        "started_at",
        "is_completed",
    )

    list_filter = (
        "is_completed",
        "started_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "course__title",
    )

    readonly_fields = (
        "started_at",
    )