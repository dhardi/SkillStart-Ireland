from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from schools.decorators import (
    school_administrator_required,
)

from .forms import (
    TicketCreateForm,
    TicketReplyForm,
)
from .models import (
    Ticket,
    TicketAttachment,
)


FINISHED_STATUSES = {
    "resolved",
    "closed",
}


def apply_ticket_filters(
    request,
    queryset,
):
    """
    Apply shared search and status filters.
    """

    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    status_filter = request.GET.get(
        "status",
        "",
    ).strip()

    valid_statuses = {
        choice[0]
        for choice in Ticket.STATUS_CHOICES
    }

    if search_query:
        queryset = queryset.filter(
            Q(
                ticket_number__icontains=(
                    search_query
                )
            )
            | Q(
                subject__icontains=search_query
            )
            | Q(
                description__icontains=search_query
            )
            | Q(
                author__first_name__icontains=(
                    search_query
                )
            )
            | Q(
                author__last_name__icontains=(
                    search_query
                )
            )
            | Q(
                author__email__icontains=(
                    search_query
                )
            )
        )

    if status_filter not in valid_statuses:
        status_filter = ""

    if status_filter:
        queryset = queryset.filter(
            status=status_filter
        )

    return (
        queryset,
        search_query,
        status_filter,
    )


def build_ticket_list_context(
    *,
    request,
    base_queryset,
    portal_type,
):
    """
    Build counters and filtered ticket list
    for either portal.
    """

    total_tickets = base_queryset.count()

    active_tickets = (
        base_queryset
        .exclude(
            status__in=FINISHED_STATUSES
        )
        .count()
    )

    waiting_support_count = (
        base_queryset
        .filter(status="waiting_support")
        .count()
    )

    resolved_tickets = (
        base_queryset
        .filter(
            status__in=FINISHED_STATUSES
        )
        .count()
    )

    filtered_queryset, search_query, status_filter = (
        apply_ticket_filters(
            request,
            base_queryset,
        )
    )

    tickets = (
        filtered_queryset
        .select_related(
            "author",
            "school",
            "assigned_to",
        )
        .order_by(
            "-updated_at",
            "-created_at",
        )
    )

    return {
        "tickets": tickets,
        "total_tickets": total_tickets,
        "active_tickets": active_tickets,
        "waiting_support_count": (
            waiting_support_count
        ),
        "resolved_tickets": resolved_tickets,
        "displayed_count": tickets.count(),
        "search_query": search_query,
        "status_filter": status_filter,
        "status_choices": Ticket.STATUS_CHOICES,
        "portal_type": portal_type,
    }


def get_visible_replies(ticket):
    """
    Return public replies only.

    Internal notes will later be available only
    inside the superadmin dashboard.
    """

    return (
        ticket.replies
        .filter(is_internal_note=False)
        .select_related("author")
        .prefetch_related("attachments")
        .order_by("created_at")
    )


def update_ticket_after_user_reply(ticket):
    """
    A reply from a student or school means that
    the ticket is waiting for platform support.
    """

    ticket.status = "waiting_support"
    ticket.resolved_at = None
    ticket.closed_at = None

    ticket.save(
        update_fields=[
            "status",
            "resolved_at",
            "closed_at",
            "updated_at",
        ]
    )


def attachment_is_public(attachment):
    """
    Prevent users from downloading attachments
    belonging to internal administrator notes.
    """

    if attachment.reply_id is None:
        return True

    return not attachment.reply.is_internal_note


def build_attachment_response(attachment):
    """
    Return an attachment as a protected download.
    """

    try:
        opened_file = attachment.file.open("rb")
    except FileNotFoundError as error:
        raise Http404(
            "The attachment file was not found."
        ) from error

    return FileResponse(
        opened_file,
        as_attachment=True,
        filename=(
            attachment.original_name
            or "attachment"
        ),
    )


# =========================================================
# STUDENT SUPPORT
# =========================================================


@login_required
def student_ticket_list(request):
    """
    Display only tickets created by the
    logged-in student.
    """

    base_queryset = Ticket.objects.filter(
        author=request.user,
    )

    context = build_ticket_list_context(
        request=request,
        base_queryset=base_queryset,
        portal_type="student",
    )

    return render(
        request,
        "support/ticket_list.html",
        context,
    )


@login_required
def student_ticket_create(request):
    """
    Create a ticket from the student area.
    """

    if request.method == "POST":
        form = TicketCreateForm(
            request.POST,
            request.FILES,
            user=request.user,
        )

        if form.is_valid():
            ticket = form.save()

            messages.success(
                request,
                (
                    f"Support ticket "
                    f"{ticket.ticket_number} "
                    "was created successfully."
                ),
            )

            return redirect(
                "support:ticket_detail",
                ticket_number=(
                    ticket.ticket_number
                ),
            )

    else:
        form = TicketCreateForm(
            user=request.user,
        )

    context = {
        "form": form,
        "portal_type": "student",
    }

    return render(
        request,
        "support/ticket_form.html",
        context,
    )


@login_required
def student_ticket_detail(
    request,
    ticket_number,
):
    """
    Display and reply to one ticket belonging
    to the logged-in student.
    """

    ticket = get_object_or_404(
        Ticket.objects.select_related(
            "author",
            "school",
            "assigned_to",
        ),
        ticket_number=ticket_number,
        author=request.user,
    )

    if request.method == "POST":
        reply_form = TicketReplyForm(
            request.POST,
            request.FILES,
        )

        if ticket.status == "closed":
            messages.error(
                request,
                (
                    "This ticket is closed and can "
                    "no longer receive replies."
                ),
            )

            return redirect(
                "support:ticket_detail",
                ticket_number=ticket.ticket_number,
            )

        if reply_form.is_valid():
            reply_form.save(
                ticket=ticket,
                author=request.user,
            )

            update_ticket_after_user_reply(
                ticket
            )

            messages.success(
                request,
                "Your reply was added successfully.",
            )

            return redirect(
                "support:ticket_detail",
                ticket_number=ticket.ticket_number,
            )

    else:
        reply_form = TicketReplyForm()

    context = {
        "ticket": ticket,
        "replies": get_visible_replies(
            ticket
        ),
        "ticket_attachments": (
            ticket.attachments
            .filter(reply__isnull=True)
            .select_related("uploaded_by")
        ),
        "reply_form": reply_form,
        "portal_type": "student",
    }

    return render(
        request,
        "support/ticket_detail.html",
        context,
    )


@login_required
def student_attachment_download(
    request,
    attachment_id,
):
    """
    Allow a student to download attachments
    from their own tickets only.
    """

    attachment = get_object_or_404(
        TicketAttachment.objects
        .select_related(
            "ticket",
            "reply",
        ),
        pk=attachment_id,
        ticket__author=request.user,
    )

    if not attachment_is_public(
        attachment
    ):
        raise Http404(
            "The attachment was not found."
        )

    return build_attachment_response(
        attachment
    )


# =========================================================
# SCHOOL SUPPORT
# =========================================================


@school_administrator_required
def school_ticket_list(request):
    """
    Display every ticket associated with the
    administrator's school.
    """

    base_queryset = Ticket.objects.filter(
        school=request.school,
    )

    context = build_ticket_list_context(
        request=request,
        base_queryset=base_queryset,
        portal_type="school",
    )

    context["school"] = request.school

    return render(
        request,
        "support/ticket_list.html",
        context,
    )


@school_administrator_required
def school_ticket_create(request):
    """
    Create a ticket automatically associated
    with the current school.
    """

    if request.method == "POST":
        form = TicketCreateForm(
            request.POST,
            request.FILES,
            user=request.user,
            portal_school=request.school,
        )

        if form.is_valid():
            ticket = form.save()

            messages.success(
                request,
                (
                    f"Support ticket "
                    f"{ticket.ticket_number} "
                    "was created successfully."
                ),
            )

            return redirect(
                "school_support:ticket_detail",
                ticket_number=(
                    ticket.ticket_number
                ),
            )

    else:
        form = TicketCreateForm(
            user=request.user,
            portal_school=request.school,
        )

    context = {
        "form": form,
        "school": request.school,
        "portal_type": "school",
    }

    return render(
        request,
        "support/ticket_form.html",
        context,
    )


@school_administrator_required
def school_ticket_detail(
    request,
    ticket_number,
):
    """
    Display and reply to a ticket associated
    with the administrator's school.
    """

    ticket = get_object_or_404(
        Ticket.objects.select_related(
            "author",
            "school",
            "assigned_to",
        ),
        ticket_number=ticket_number,
        school=request.school,
    )

    if request.method == "POST":
        reply_form = TicketReplyForm(
            request.POST,
            request.FILES,
        )

        if ticket.status == "closed":
            messages.error(
                request,
                (
                    "This ticket is closed and can "
                    "no longer receive replies."
                ),
            )

            return redirect(
                "school_support:ticket_detail",
                ticket_number=ticket.ticket_number,
            )

        if reply_form.is_valid():
            reply_form.save(
                ticket=ticket,
                author=request.user,
            )

            update_ticket_after_user_reply(
                ticket
            )

            messages.success(
                request,
                "Your reply was added successfully.",
            )

            return redirect(
                "school_support:ticket_detail",
                ticket_number=ticket.ticket_number,
            )

    else:
        reply_form = TicketReplyForm()

    context = {
        "ticket": ticket,
        "replies": get_visible_replies(
            ticket
        ),
        "ticket_attachments": (
            ticket.attachments
            .filter(reply__isnull=True)
            .select_related("uploaded_by")
        ),
        "reply_form": reply_form,
        "school": request.school,
        "portal_type": "school",
    }

    return render(
        request,
        "support/ticket_detail.html",
        context,
    )


@school_administrator_required
def school_attachment_download(
    request,
    attachment_id,
):
    """
    Allow a school administrator to download
    attachments from their school's tickets only.
    """

    attachment = get_object_or_404(
        TicketAttachment.objects
        .select_related(
            "ticket",
            "reply",
        ),
        pk=attachment_id,
        ticket__school=request.school,
    )

    if not attachment_is_public(
        attachment
    ):
        raise Http404(
            "The attachment was not found."
        )

    return build_attachment_response(
        attachment
    )