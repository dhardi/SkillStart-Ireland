from django.contrib import admin

from .models import Enrollment, LessonProgress


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


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = (
        "enrollment",
        "lesson",
        "completed",
        "completed_at",
    )

    list_filter = (
        "completed",
        "lesson__course",
    )

    search_fields = (
        "lesson__title",
        "enrollment__user__username",
        "enrollment__course__title",
    )

    autocomplete_fields = (
        "enrollment",
        "lesson",
    )