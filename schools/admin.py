from django.contrib import admin

from .models import School, SchoolAdministrator


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "plan",
        "student_limit",
        "active_student_count",
        "subscription_active",
        "is_active",
        "created_at",
    )

    list_filter = (
        "plan",
        "subscription_active",
        "is_active",
        "created_at",
    )

    search_fields = (
        "name",
        "contact_email",
        "phone_number",
    )

    prepopulated_fields = {
        "slug": (
            "name",
        ),
    }

    readonly_fields = (
        "created_at",
        "updated_at",
        "active_student_count",
    )

    fieldsets = (
        (
            "School information",
            {
                "fields": (
                    "name",
                    "slug",
                    "logo",
                    "contact_email",
                    "phone_number",
                ),
            },
        ),
        (
            "Plan and subscription",
            {
                "fields": (
                    "plan",
                    "student_limit",
                    "active_student_count",
                    "subscription_active",
                    "subscription_end_date",
                ),
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "is_active",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )


@admin.register(SchoolAdministrator)
class SchoolAdministratorAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "school",
        "is_active",
        "created_at",
    )

    list_filter = (
        "school",
        "is_active",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
        "school__name",
    )

    autocomplete_fields = (
        "user",
        "school",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )