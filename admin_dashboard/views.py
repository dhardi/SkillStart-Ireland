from django.contrib import messages
from django.contrib.admin.views.decorators import (
    staff_member_required,
)
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from accounts.models import Enrollment, LessonProgress
from courses.models import Category, Course, Lesson
from support.forms import (
    StaffTicketReplyForm,
    StaffTicketUpdateForm,
)
from support.models import (
    Ticket,
    TicketAttachment,
)

from .forms import EnrollmentForm, LessonForm


User = get_user_model()


SUPPORT_FINISHED_STATUSES = {
    "resolved",
    "closed",
}


@staff_member_required
def dashboard(request):
    context = {
        "total_students": User.objects.filter(
            is_staff=False,
        ).count(),
        "total_courses": Course.objects.count(),
        "published_courses": Course.objects.filter(
            is_published=True,
        ).count(),
        "total_lessons": Lesson.objects.count(),
        "total_enrollments": Enrollment.objects.count(),
        "completed_courses": Enrollment.objects.filter(
            is_completed=True,
        ).count(),
        "completed_lessons": LessonProgress.objects.filter(
            completed=True,
        ).count(),
    }

    return render(
        request,
        "admin_dashboard/dashboard.html",
        context,
    )


@staff_member_required
def course_list(request):
    search_query = request.GET.get(
        "search",
        "",
    ).strip()

    selected_category = request.GET.get(
        "category",
        "",
    ).strip()

    selected_status = request.GET.get(
        "status",
        "",
    ).strip()

    courses = (
        Course.objects
        .select_related("category")
        .annotate(
            lesson_count=Count(
                "lessons",
                distinct=True,
            ),
            enrollment_count=Count(
                "enrollments",
                distinct=True,
            ),
        )
        .order_by("-created_at")
    )

    if search_query:
        courses = courses.filter(
            Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(category__name__icontains=search_query)
        )

    if selected_category:
        courses = courses.filter(
            category__slug=selected_category,
        )

    if selected_status == "published":
        courses = courses.filter(
            is_published=True,
        )

    elif selected_status == "draft":
        courses = courses.filter(
            is_published=False,
        )

    categories = Category.objects.order_by(
        "name",
    )

    context = {
        "courses": courses,
        "categories": categories,
        "search_query": search_query,
        "selected_category": selected_category,
        "selected_status": selected_status,
        "filtered_course_count": courses.count(),
    }

    return render(
        request,
        "admin_dashboard/course_list.html",
        context,
    )

@staff_member_required
def student_list(request):
    search_query = request.GET.get(
        "search",
        "",
    ).strip()

    selected_status = request.GET.get(
        "status",
        "",
    ).strip()

    students = (
        User.objects
        .filter(
            is_staff=False,
        )
        .annotate(
            enrollment_count=Count(
                "enrollments",
                distinct=True,
            ),
            completed_course_count=Count(
                "enrollments",
                filter=Q(
                    enrollments__is_completed=True,
                ),
                distinct=True,
            ),
            completed_lesson_count=Count(
                "enrollments__lesson_progress",
                filter=Q(
                    enrollments__lesson_progress__completed=True,
                ),
                distinct=True,
            ),
        )
        .order_by(
            "-date_joined",
        )
    )

    if search_query:
        students = students.filter(
            Q(username__icontains=search_query)
            | Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(email__icontains=search_query)
        )

    if selected_status == "active":
        students = students.filter(
            is_active=True,
        )

    elif selected_status == "inactive":
        students = students.filter(
            is_active=False,
        )

    context = {
        "students": students,
        "search_query": search_query,
        "selected_status": selected_status,
        "filtered_student_count": students.count(),
    }

    return render(
        request,
        "admin_dashboard/student_list.html",
        context,
    )

@staff_member_required
def student_detail(request, student_id):
    student = get_object_or_404(
        User.objects.filter(
            is_staff=False,
        ),
        id=student_id,
    )

    if request.method == "POST":
        action = request.POST.get(
            "action",
            "",
        )

        if action == "deactivate":
            student.is_active = False
            student.save(
                update_fields=["is_active"],
            )

            messages.success(
                request,
                (
                    f"{student.username}'s account "
                    "has been deactivated."
                ),
            )

        elif action == "activate":
            student.is_active = True
            student.save(
                update_fields=["is_active"],
            )

            messages.success(
                request,
                (
                    f"{student.username}'s account "
                    "has been activated."
                ),
            )

        return redirect(
            "admin_dashboard:student_detail",
            student_id=student.id,
        )

    enrollments = list(
        Enrollment.objects
        .filter(
            user=student,
        )
        .select_related(
            "course",
            "course__category",
        )
        .order_by(
            "-started_at",
        )
    )

    total_completed_lessons = 0

    for enrollment in enrollments:
        total_lessons = (
            enrollment.course.lessons
            .filter(
                is_published=True,
            )
            .count()
        )

        completed_lessons = (
            LessonProgress.objects
            .filter(
                enrollment=enrollment,
                completed=True,
                lesson__is_published=True,
            )
            .count()
        )

        if total_lessons > 0:
            progress_percentage = round(
                completed_lessons
                / total_lessons
                * 100
            )
        else:
            progress_percentage = 0

        enrollment.total_lessons = total_lessons
        enrollment.completed_lessons = (
            completed_lessons
        )
        enrollment.progress_percentage = (
            progress_percentage
        )

        total_completed_lessons += (
            completed_lessons
        )

    completed_courses = sum(
        1
        for enrollment in enrollments
        if enrollment.is_completed
    )

    context = {
        "student": student,
        "enrollments": enrollments,
        "total_enrollments": len(
            enrollments
        ),
        "total_completed_lessons": (
            total_completed_lessons
        ),
        "completed_courses": completed_courses,
    }

    return render(
        request,
        "admin_dashboard/student_detail.html",
        context,
    )

@staff_member_required
def enrollment_list(request):
    search_query = request.GET.get(
        "search",
        "",
    ).strip()

    selected_course = request.GET.get(
        "course",
        "",
    ).strip()

    selected_status = request.GET.get(
        "status",
        "",
    ).strip()

    enrollments = list(
        Enrollment.objects
        .select_related(
            "user",
            "course",
            "course__category",
        )
        .order_by("-started_at")
    )

    if search_query:
        enrollments = [
            enrollment
            for enrollment in enrollments
            if (
                search_query.lower()
                in enrollment.user.username.lower()
                or search_query.lower()
                in enrollment.user.first_name.lower()
                or search_query.lower()
                in enrollment.user.last_name.lower()
                or search_query.lower()
                in enrollment.user.email.lower()
                or search_query.lower()
                in enrollment.course.title.lower()
            )
        ]

    if selected_course:
        enrollments = [
            enrollment
            for enrollment in enrollments
            if enrollment.course.slug == selected_course
        ]

    if selected_status == "completed":
        enrollments = [
            enrollment
            for enrollment in enrollments
            if enrollment.is_completed
        ]

    elif selected_status == "in_progress":
        enrollments = [
            enrollment
            for enrollment in enrollments
            if not enrollment.is_completed
        ]

    for enrollment in enrollments:
        total_lessons = (
            enrollment.course.lessons
            .filter(
                is_published=True,
            )
            .count()
        )

        completed_lessons = (
            LessonProgress.objects
            .filter(
                enrollment=enrollment,
                completed=True,
                lesson__is_published=True,
            )
            .count()
        )

        if total_lessons > 0:
            progress_percentage = round(
                completed_lessons
                / total_lessons
                * 100
            )
        else:
            progress_percentage = 0

        enrollment.total_lessons = total_lessons
        enrollment.completed_lessons = (
            completed_lessons
        )
        enrollment.progress_percentage = (
            progress_percentage
        )

    courses = (
        Course.objects
        .order_by("title")
    )

    context = {
        "enrollments": enrollments,
        "courses": courses,
        "search_query": search_query,
        "selected_course": selected_course,
        "selected_status": selected_status,
        "filtered_enrollment_count": len(
            enrollments
        ),
    }

    return render(
        request,
        "admin_dashboard/enrollment_list.html",
        context,
    )

@staff_member_required
def enrollment_create(request):
    initial_data = {}

    student_id = request.GET.get(
        "student",
        "",
    ).strip()

    if student_id.isdigit():
        initial_data["user"] = student_id

    if request.method == "POST":
        form = EnrollmentForm(
            request.POST,
        )

        if form.is_valid():
            enrollment = form.save()

            messages.success(
                request,
                (
                    f"{enrollment.user.username} "
                    f"has been enrolled in "
                    f"{enrollment.course.title}."
                ),
            )

            return redirect(
                "admin_dashboard:student_detail",
                student_id=enrollment.user.id,
            )

    else:
        form = EnrollmentForm(
            initial=initial_data,
        )

    context = {
        "form": form,
    }

    return render(
        request,
        "admin_dashboard/enrollment_form.html",
        context,
    )

@staff_member_required
def lesson_list(request):
    search_query = request.GET.get(
        "search",
        "",
    ).strip()

    selected_course = request.GET.get(
        "course",
        "",
    ).strip()

    selected_status = request.GET.get(
        "status",
        "",
    ).strip()

    lessons = (
        Lesson.objects
        .select_related(
            "course",
            "course__category",
        )
        .order_by(
            "course__title",
            "order",
            "title",
        )
    )

    if search_query:
        lessons = lessons.filter(
            Q(title__icontains=search_query)
            | Q(content__icontains=search_query)
            | Q(course__title__icontains=search_query)
        )

    if selected_course:
        lessons = lessons.filter(
            course__slug=selected_course,
        )

    if selected_status == "published":
        lessons = lessons.filter(
            is_published=True,
        )

    elif selected_status == "draft":
        lessons = lessons.filter(
            is_published=False,
        )

    courses = (
        Course.objects
        .select_related("category")
        .order_by("title")
    )

    context = {
        "lessons": lessons,
        "courses": courses,
        "search_query": search_query,
        "selected_course": selected_course,
        "selected_status": selected_status,
        "filtered_lesson_count": lessons.count(),
    }

    return render(
        request,
        "admin_dashboard/lesson_list.html",
        context,
    )


@staff_member_required
def lesson_create(request):
    if request.method == "POST":
        form = LessonForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Lesson created successfully.",
            )

            return redirect(
                "admin_dashboard:lesson_list"
            )
    else:
        form = LessonForm()

    context = {
        "form": form,
        "page_heading": "Add Lesson",
        "submit_text": "Create Lesson",
    }

    return render(
        request,
        "admin_dashboard/lesson_form.html",
        context,
    )


@staff_member_required
def lesson_update(request, lesson_id):
    lesson = get_object_or_404(
        Lesson.objects.select_related(
            "course",
            "course__category",
        ),
        id=lesson_id,
    )

    if request.method == "POST":
        form = LessonForm(
            request.POST,
            request.FILES,
            instance=lesson,
        )

        if form.is_valid():
            lesson = form.save()

            messages.success(
                request,
                (
                    f'The lesson "{lesson.title}" '
                    "has been updated successfully."
                ),
            )

            return redirect(
                "admin_dashboard:lesson_list",
            )

    else:
        form = LessonForm(
            instance=lesson,
        )

    context = {
        "form": form,
        "page_heading": "Edit lesson",
        "page_description": (
            "Update the lesson content, position "
            "or publication status."
        ),
        "submit_text": "Save changes",
        "lesson": lesson,
    }

    return render(
        request,
        "admin_dashboard/lesson_form.html",
        context,
    )


@staff_member_required
def lesson_delete(request, lesson_id):
    lesson = get_object_or_404(
        Lesson.objects.select_related(
            "course",
        ),
        id=lesson_id,
    )

    if request.method == "POST":
        lesson_title = lesson.title
        course_title = lesson.course.title

        lesson.delete()

        messages.success(
            request,
            (
                f'The lesson "{lesson_title}" from '
                f'"{course_title}" has been deleted.'
            ),
        )

        return redirect(
            "admin_dashboard:lesson_list",
        )

    context = {
        "lesson": lesson,
    }

    return render(
        request,
        "admin_dashboard/lesson_confirm_delete.html",
        context,
    )

@staff_member_required
def support_ticket_list(request):
    """
    Display and filter all support tickets
    across the platform.
    """

    search_query = request.GET.get(
        "search",
        "",
    ).strip()

    selected_status = request.GET.get(
        "status",
        "",
    ).strip()

    selected_priority = request.GET.get(
        "priority",
        "",
    ).strip()

    selected_category = request.GET.get(
        "category",
        "",
    ).strip()

    selected_assignment = request.GET.get(
        "assignment",
        "",
    ).strip()

    base_queryset = Ticket.objects.all()

    total_tickets = base_queryset.count()

    active_tickets = (
        base_queryset
        .exclude(
            status__in=SUPPORT_FINISHED_STATUSES,
        )
        .count()
    )

    new_tickets = (
        base_queryset
        .filter(status="new")
        .count()
    )

    waiting_support_count = (
        base_queryset
        .filter(status="waiting_support")
        .count()
    )

    urgent_tickets = (
        base_queryset
        .filter(
            priority="urgent",
        )
        .exclude(
            status__in=SUPPORT_FINISHED_STATUSES,
        )
        .count()
    )

    tickets = base_queryset

    if search_query:
        tickets = tickets.filter(
            Q(
                ticket_number__icontains=search_query
            )
            | Q(
                subject__icontains=search_query
            )
            | Q(
                description__icontains=search_query
            )
            | Q(
                author__username__icontains=search_query
            )
            | Q(
                author__first_name__icontains=search_query
            )
            | Q(
                author__last_name__icontains=search_query
            )
            | Q(
                author__email__icontains=search_query
            )
            | Q(
                school__name__icontains=search_query
            )
        )

    valid_statuses = {
        value
        for value, label in Ticket.STATUS_CHOICES
    }

    valid_priorities = {
        value
        for value, label in Ticket.PRIORITY_CHOICES
    }

    valid_categories = {
        value
        for value, label in Ticket.CATEGORY_CHOICES
    }

    if selected_status not in valid_statuses:
        selected_status = ""

    if selected_priority not in valid_priorities:
        selected_priority = ""

    if selected_category not in valid_categories:
        selected_category = ""

    if selected_status:
        tickets = tickets.filter(
            status=selected_status,
        )

    if selected_priority:
        tickets = tickets.filter(
            priority=selected_priority,
        )

    if selected_category:
        tickets = tickets.filter(
            category=selected_category,
        )

    if selected_assignment == "assigned":
        tickets = tickets.filter(
            assigned_to__isnull=False,
        )

    elif selected_assignment == "unassigned":
        tickets = tickets.filter(
            assigned_to__isnull=True,
        )

    elif selected_assignment == "mine":
        tickets = tickets.filter(
            assigned_to=request.user,
        )

    elif selected_assignment:
        selected_assignment = ""

    tickets = (
        tickets
        .select_related(
            "author",
            "school",
            "assigned_to",
        )
        .annotate(
            reply_count=Count(
                "replies",
                distinct=True,
            )
        )
        .order_by(
            "-updated_at",
            "-created_at",
        )
    )

    context = {
        "tickets": tickets,
        "total_tickets": total_tickets,
        "active_tickets": active_tickets,
        "new_tickets": new_tickets,
        "waiting_support_count": waiting_support_count,
        "urgent_tickets": urgent_tickets,
        "filtered_ticket_count": tickets.count(),
        "search_query": search_query,
        "selected_status": selected_status,
        "selected_priority": selected_priority,
        "selected_category": selected_category,
        "selected_assignment": selected_assignment,
        "status_choices": Ticket.STATUS_CHOICES,
        "priority_choices": Ticket.PRIORITY_CHOICES,
        "category_choices": Ticket.CATEGORY_CHOICES,
    }

    return render(
        request,
        "admin_dashboard/support_ticket_list.html",
        context,
    )


@staff_member_required
def support_ticket_detail(
    request,
    ticket_number,
):
    """
    Manage one support ticket, including status,
    assignment, public replies and internal notes.
    """

    ticket = get_object_or_404(
        Ticket.objects.select_related(
            "author",
            "school",
            "assigned_to",
        ),
        ticket_number=ticket_number,
    )

    update_form = StaffTicketUpdateForm(
        instance=ticket,
        prefix="management",
    )

    reply_form = StaffTicketReplyForm(
        prefix="reply",
    )

    if request.method == "POST":
        action = request.POST.get(
            "action",
            "",
        )

        if action == "update_ticket":
            update_form = StaffTicketUpdateForm(
                request.POST,
                instance=ticket,
                prefix="management",
            )

            if update_form.is_valid():
                ticket = update_form.save()

                messages.success(
                    request,
                    (
                        f"Ticket {ticket.ticket_number} "
                        "was updated successfully."
                    ),
                )

                return redirect(
                    "admin_dashboard:support_ticket_detail",
                    ticket_number=ticket.ticket_number,
                )

        elif action == "add_reply":
            reply_form = StaffTicketReplyForm(
                request.POST,
                request.FILES,
                prefix="reply",
            )

            if ticket.status == "closed":
                messages.error(
                    request,
                    (
                        "Closed tickets cannot receive "
                        "new replies or notes."
                    ),
                )

                return redirect(
                    "admin_dashboard:support_ticket_detail",
                    ticket_number=ticket.ticket_number,
                )

            if reply_form.is_valid():
                reply = reply_form.save(
                    ticket=ticket,
                    author=request.user,
                )

                if reply.is_internal_note:
                    messages.success(
                        request,
                        "Internal note added successfully.",
                    )

                else:
                    messages.success(
                        request,
                        (
                            "The reply was sent and the ticket "
                            "is now waiting for the user."
                        ),
                    )

                return redirect(
                    "admin_dashboard:support_ticket_detail",
                    ticket_number=ticket.ticket_number,
                )

        elif action == "assign_to_me":
            ticket.assigned_to = request.user

            if ticket.status == "new":
                ticket.status = "open"

            ticket.save(
                update_fields=[
                    "assigned_to",
                    "status",
                    "updated_at",
                ]
            )

            messages.success(
                request,
                (
                    f"Ticket {ticket.ticket_number} "
                    "was assigned to you."
                ),
            )

            return redirect(
                "admin_dashboard:support_ticket_detail",
                ticket_number=ticket.ticket_number,
            )

        elif action == "reopen_ticket":
            ticket.status = "open"
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

            messages.success(
                request,
                (
                    f"Ticket {ticket.ticket_number} "
                    "was reopened."
                ),
            )

            return redirect(
                "admin_dashboard:support_ticket_detail",
                ticket_number=ticket.ticket_number,
            )

    replies = (
        ticket.replies
        .select_related("author")
        .prefetch_related("attachments")
        .order_by("created_at")
    )

    ticket_attachments = (
        ticket.attachments
        .filter(reply__isnull=True)
        .select_related("uploaded_by")
    )

    context = {
        "ticket": ticket,
        "replies": replies,
        "ticket_attachments": ticket_attachments,
        "update_form": update_form,
        "reply_form": reply_form,
    }

    return render(
        request,
        "admin_dashboard/support_ticket_detail.html",
        context,
    )


@staff_member_required
def support_attachment_download(
    request,
    attachment_id,
):
    """
    Download any support attachment through
    the protected management area.
    """

    attachment = get_object_or_404(
        TicketAttachment.objects.select_related(
            "ticket",
            "reply",
        ),
        pk=attachment_id,
    )

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
