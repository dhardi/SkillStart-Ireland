from django.contrib import admin

from .models import (
    Ticket,
    TicketAttachment,
    TicketReply,
)


class TicketReplyInline(admin.TabularInline):
    model = TicketReply
    extra = 0

    fields = (
        "author",
        "message",
        "is_internal_note",
        "created_at",
    )

    readonly_fields = (
        "created_at",
    )


class TicketAttachmentInline(admin.TabularInline):
    model = TicketAttachment
    extra = 0

    fields = (
        "uploaded_by",
        "file",
        "original_name",
        "reply",
        "uploaded_at",
    )

    readonly_fields = (
        "original_name",
        "uploaded_at",
    )


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "ticket_number",
        "subject",
        "author",
        "school",
        "category",
        "priority",
        "status",
        "assigned_to",
        "updated_at",
    )

    list_filter = (
        "status",
        "priority",
        "category",
        "school",
        "created_at",
    )

    search_fields = (
        "ticket_number",
        "subject",
        "description",
        "author__username",
        "author__first_name",
        "author__last_name",
        "author__email",
        "school__name",
    )

    readonly_fields = (
        "ticket_number",
        "created_at",
        "updated_at",
        "resolved_at",
        "closed_at",
    )

    fieldsets = (
        (
            "Ticket",
            {
                "fields": (
                    "ticket_number",
                    "subject",
                    "description",
                    "category",
                    "priority",
                    "status",
                )
            },
        ),
        (
            "People and school",
            {
                "fields": (
                    "author",
                    "school",
                    "assigned_to",
                )
            },
        ),
        (
            "Dates",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "resolved_at",
                    "closed_at",
                )
            },
        ),
    )

    inlines = (
        TicketReplyInline,
        TicketAttachmentInline,
    )

    ordering = (
        "-updated_at",
    )


@admin.register(TicketReply)
class TicketReplyAdmin(admin.ModelAdmin):
    list_display = (
        "ticket",
        "author",
        "is_internal_note",
        "created_at",
    )

    list_filter = (
        "is_internal_note",
        "created_at",
    )

    search_fields = (
        "ticket__ticket_number",
        "ticket__subject",
        "author__username",
        "author__email",
        "message",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = (
        "original_name",
        "ticket",
        "reply",
        "uploaded_by",
        "uploaded_at",
    )

    search_fields = (
        "original_name",
        "ticket__ticket_number",
        "uploaded_by__username",
        "uploaded_by__email",
    )

    readonly_fields = (
        "original_name",
        "uploaded_at",
    )