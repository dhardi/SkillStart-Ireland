import logging
from django.http import FileResponse
from django.urls import reverse

from courses.certificate_pdf import build_certificate_pdf
from courses.models import Course

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Count, Prefetch, Q
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from accounts.models import (
    AssessmentAttempt,
    Certificate,
    Enrollment,
)

from .decorators import school_administrator_required
from .forms import (
    SchoolEnrollmentForm,
    SchoolStudentCreateForm,
)

from .services import send_student_invitation


logger = logging.getLogger(__name__)


User = get_user_model()


@school_administrator_required
def dashboard(request):
    """
    Display the dashboard for the school connected
    to the logged-in administrator.
    """

    school = request.school

    school_enrollments = (
        Enrollment.objects
        .filter(school=school)
        .select_related(
            "user",
            "course",
        )
    )

    total_students = (
        school_enrollments
        .values("user")
        .distinct()
        .count()
    )

    total_enrollments = school_enrollments.count()

    active_enrollments = (
        school_enrollments
        .filter(is_completed=False)
        .count()
    )

    completed_courses = (
        school_enrollments
        .filter(is_completed=True)
        .count()
    )

    certificate_count = (
        Certificate.objects
        .filter(
            enrollment__school=school,
        )
        .count()
    )

    recent_enrollments = (
        school_enrollments
        .order_by("-started_at")[:5]
    )

    if school.student_limit > 0:
        student_capacity_percentage = min(
            round(
                total_students
                / school.student_limit
                * 100
            ),
            100,
        )
    else:
        student_capacity_percentage = 0

    context = {
        "school": school,
        "school_administrator": (
            request.school_administrator
        ),
        "total_students": total_students,
        "total_enrollments": total_enrollments,
        "active_enrollments": active_enrollments,
        "completed_courses": completed_courses,
        "certificate_count": certificate_count,
        "recent_enrollments": recent_enrollments,
        "student_capacity_percentage": (
            student_capacity_percentage
        ),
    }

    return render(
        request,
        "schools/dashboard.html",
        context,
    )


@school_administrator_required
def student_list(request):
    """
    Display students who have at least one enrollment
    connected to the administrator's school.
    """

    school = request.school

    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    school_enrollments = (
        Enrollment.objects
        .filter(school=school)
        .select_related(
            "user",
            "course",
        )
    )

    if search_query:
        school_enrollments = school_enrollments.filter(
            Q(
                user__first_name__icontains=search_query
            )
            | Q(
                user__last_name__icontains=search_query
            )
            | Q(
                user__username__icontains=search_query
            )
            | Q(
                user__email__icontains=search_query
            )
        )

    school_enrollments = (
        school_enrollments
        .annotate(
            published_lesson_count=Count(
                "course__lessons",
                filter=Q(
                    course__lessons__is_published=True
                ),
                distinct=True,
            ),
            completed_lesson_count=Count(
                "lesson_progress",
                filter=Q(
                    lesson_progress__completed=True,
                    lesson_progress__lesson__is_published=True,
                ),
                distinct=True,
            ),
            enrollment_certificate_count=Count(
                "certificate",
                distinct=True,
            ),
        )
        .order_by(
            "user__first_name",
            "user__last_name",
            "user__username",
            "course__title",
        )
    )

    students_by_id = {}

    for enrollment in school_enrollments:
        user = enrollment.user

        if user.pk not in students_by_id:
            display_name = (
                user.get_full_name().strip()
                or user.username
            )

            students_by_id[user.pk] = {
                "user": user,
                "display_name": display_name,
                "enrollment_count": 0,
                "completed_course_count": 0,
                "total_lesson_count": 0,
                "completed_lesson_count": 0,
                "certificate_count": 0,
                "progress_percentage": 0,
            }

        student_data = students_by_id[user.pk]

        student_data["enrollment_count"] += 1

        if enrollment.is_completed:
            student_data[
                "completed_course_count"
            ] += 1

        student_data[
            "total_lesson_count"
        ] += enrollment.published_lesson_count

        student_data[
            "completed_lesson_count"
        ] += enrollment.completed_lesson_count

        student_data[
            "certificate_count"
        ] += enrollment.enrollment_certificate_count

    student_rows = list(
        students_by_id.values()
    )

    for student_data in student_rows:
        total_lessons = student_data[
            "total_lesson_count"
        ]

        completed_lessons = student_data[
            "completed_lesson_count"
        ]

        if total_lessons > 0:
            student_data[
                "progress_percentage"
            ] = min(
                round(
                    completed_lessons
                    / total_lessons
                    * 100
                ),
                100,
            )

        elif (
            student_data["enrollment_count"] > 0
            and student_data["completed_course_count"]
            == student_data["enrollment_count"]
        ):
            student_data[
                "progress_percentage"
            ] = 100

    student_rows.sort(
        key=lambda student: (
            student["display_name"].lower()
        ),
    )

    context = {
        "school": school,
        "student_rows": student_rows,
        "search_query": search_query,
        "student_count": len(student_rows),
    }

    return render(
        request,
        "schools/students.html",
        context,
    )


@school_administrator_required
def enrollment_list(request):
    """
    Display all enrolments connected to the logged-in
    administrator's school.
    """

    school = request.school

    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    course_value = request.GET.get(
        "course",
        "",
    ).strip()

    status_filter = request.GET.get(
        "status",
        "",
    ).strip()

    selected_course_id = None

    school_enrollments = Enrollment.objects.filter(
        school=school,
    )

    total_enrollments = school_enrollments.count()

    active_enrollments = (
        school_enrollments
        .filter(is_completed=False)
        .count()
    )

    completed_enrollments = (
        school_enrollments
        .filter(is_completed=True)
        .count()
    )

    certificate_count = (
        Certificate.objects
        .filter(enrollment__school=school)
        .count()
    )

    filtered_enrollments = school_enrollments

    if search_query:
        filtered_enrollments = filtered_enrollments.filter(
            Q(
                user__first_name__icontains=search_query
            )
            | Q(
                user__last_name__icontains=search_query
            )
            | Q(
                user__username__icontains=search_query
            )
            | Q(
                user__email__icontains=search_query
            )
            | Q(
                course__title__icontains=search_query
            )
            | Q(
                course__category__name__icontains=search_query
            )
        )

    if course_value:
        try:
            selected_course_id = int(course_value)
        except (TypeError, ValueError):
            selected_course_id = None
        else:
            filtered_enrollments = (
                filtered_enrollments
                .filter(course_id=selected_course_id)
            )

    allowed_statuses = {
        "",
        "in_progress",
        "completed",
    }

    if status_filter not in allowed_statuses:
        status_filter = ""

    if status_filter == "in_progress":
        filtered_enrollments = (
            filtered_enrollments
            .filter(is_completed=False)
        )

    elif status_filter == "completed":
        filtered_enrollments = (
            filtered_enrollments
            .filter(is_completed=True)
        )

    completed_attempts = (
        AssessmentAttempt.objects
        .filter(is_completed=True)
        .select_related("assessment")
        .order_by(
            "-completed_at",
            "-started_at",
        )
    )

    enrollments = (
        filtered_enrollments
        .select_related(
            "user",
            "course",
            "course__category",
            "certificate",
        )
        .annotate(
            published_lesson_count=Count(
                "course__lessons",
                filter=Q(
                    course__lessons__is_published=True,
                ),
                distinct=True,
            ),
            completed_lesson_count=Count(
                "lesson_progress",
                filter=Q(
                    lesson_progress__completed=True,
                    lesson_progress__lesson__is_published=True,
                ),
                distinct=True,
            ),
        )
        .prefetch_related(
            Prefetch(
                "assessment_attempts",
                queryset=completed_attempts,
                to_attr="completed_attempts",
            )
        )
        .order_by("-started_at")
    )

    enrollment_rows = []

    for enrollment in enrollments:
        total_lessons = (
            enrollment.published_lesson_count
        )

        completed_lessons = (
            enrollment.completed_lesson_count
        )

        if total_lessons > 0:
            progress_percentage = min(
                round(
                    completed_lessons
                    / total_lessons
                    * 100
                ),
                100,
            )

        elif enrollment.is_completed:
            progress_percentage = 100

        else:
            progress_percentage = 0

        latest_attempt = None

        if enrollment.completed_attempts:
            latest_attempt = (
                enrollment.completed_attempts[0]
            )

        try:
            certificate = enrollment.certificate
        except Certificate.DoesNotExist:
            certificate = None

        display_name = (
            enrollment.user.get_full_name().strip()
            or enrollment.user.username
        )

        enrollment_rows.append(
            {
                "enrollment": enrollment,
                "display_name": display_name,
                "published_lesson_count": total_lessons,
                "completed_lesson_count": completed_lessons,
                "progress_percentage": progress_percentage,
                "latest_attempt": latest_attempt,
                "certificate": certificate,
            }
        )

    available_courses = (
        Course.objects
        .filter(
            enrollments__school=school,
        )
        .select_related("category")
        .distinct()
        .order_by(
            "category__name",
            "title",
        )
    )

    context = {
        "school": school,
        "enrollment_rows": enrollment_rows,
        "total_enrollments": total_enrollments,
        "active_enrollments": active_enrollments,
        "completed_enrollments": completed_enrollments,
        "certificate_count": certificate_count,
        "displayed_count": len(enrollment_rows),
        "available_courses": available_courses,
        "search_query": search_query,
        "selected_course_id": selected_course_id,
        "status_filter": status_filter,
    }

    return render(
        request,
        "schools/enrollments.html",
        context,
    )







@school_administrator_required
def enrollment_create(request):
    """
    Enroll an existing student in a published course
    through the administrator's school.
    """

    school = request.school

    if request.method == "POST":
        form = SchoolEnrollmentForm(
            request.POST,
            school=school,
        )

        if form.is_valid():
            enrollment = form.save()

            student_name = (
                enrollment.user.get_full_name().strip()
                or enrollment.user.username
            )

            messages.success(
                request,
                (
                    f"{student_name} has been enrolled in "
                    f"{enrollment.course.title} successfully."
                ),
            )

            return redirect(
                "schools:enrollment_list",
            )

    else:
        form = SchoolEnrollmentForm(
            school=school,
        )

    context = {
        "school": school,
        "form": form,
        "current_student_count": (
            school.active_student_count
        ),
        "available_student_places": max(
            school.student_limit
            - school.active_student_count,
            0,
        ),
    }

    return render(
        request,
        "schools/enrollment_form.html",
        context,
    )


@school_administrator_required
def student_create(request):
    """
    Create a new student account, profile and
    initial enrolment through the school portal.
    """

    school = request.school

    if request.method == "POST":
        form = SchoolStudentCreateForm(
            request.POST,
            school=school,
        )

        if form.is_valid():
            student, enrollment = form.save()

            invitation_sent = False

            try:
                send_student_invitation(
                    request=request,
                    student=student,
                    school=school,
                    course=enrollment.course,
                )

                invitation_sent = True

            except Exception:
                logger.exception(
                    "Student invitation email failed "
                    "for user ID %s.",
                    student.pk,
                )

            student_name = (
                student.get_full_name().strip()
                or student.username
            )

            if invitation_sent:
                messages.success(
                    request,
                    (
                        f"{student_name} was created and enrolled "
                        f"in {enrollment.course.title}. "
                        f"The password invitation was sent to "
                        f"{student.email}."
                    ),
                )

            else:
                messages.warning(
                    request,
                    (
                        f"{student_name} was created and enrolled, "
                        "but the invitation email could not be sent. "
                        "Please contact the platform administrator."
                    ),
                )

            return redirect(
                "schools:student_detail",
                student_id=student.pk,
            )

    else:
        form = SchoolStudentCreateForm(
            school=school,
        )

    current_student_count = (
        school.active_student_count
    )

    available_student_places = max(
        school.student_limit
        - current_student_count,
        0,
    )

    context = {
        "school": school,
        "form": form,
        "current_student_count": current_student_count,
        "available_student_places": (
            available_student_places
        ),
    }

    return render(
        request,
        "schools/student_form.html",
        context,
    )

@school_administrator_required
def student_detail(request, student_id):
    """
    Display one student and only the enrollments
    connected to the administrator's school.
    """

    school = request.school

    student = get_object_or_404(
        User.objects
        .filter(
            pk=student_id,
            enrollments__school=school,
        )
        .distinct()
    )

    enrollments = (
        Enrollment.objects
        .filter(
            school=school,
            user=student,
        )
        .select_related(
            "course",
            "course__category",
        )
        .annotate(
            published_lesson_count=Count(
                "course__lessons",
                filter=Q(
                    course__lessons__is_published=True,
                ),
                distinct=True,
            ),
            completed_lesson_count=Count(
                "lesson_progress",
                filter=Q(
                    lesson_progress__completed=True,
                    lesson_progress__lesson__is_published=True,
                ),
                distinct=True,
            ),
        )
        .order_by(
            "-started_at",
        )
    )

    enrollment_rows = []

    total_lessons = 0
    completed_lessons = 0
    completed_courses = 0
    certificate_count = 0

    for enrollment in enrollments:
        published_count = (
            enrollment.published_lesson_count
        )

        completed_count = (
            enrollment.completed_lesson_count
        )

        total_lessons += published_count
        completed_lessons += completed_count

        if published_count > 0:
            progress_percentage = min(
                round(
                    completed_count
                    / published_count
                    * 100
                ),
                100,
            )

        elif enrollment.is_completed:
            progress_percentage = 100

        else:
            progress_percentage = 0

        if enrollment.is_completed:
            completed_courses += 1

        latest_attempt = (
            enrollment.assessment_attempts
            .filter(
                is_completed=True,
            )
            .select_related(
                "assessment",
            )
            .order_by(
                "-completed_at",
                "-started_at",
            )
            .first()
        )

        try:
            certificate = enrollment.certificate

        except Certificate.DoesNotExist:
            certificate = None

        if certificate:
            certificate_count += 1

        enrollment_rows.append(
            {
                "enrollment": enrollment,
                "progress_percentage": (
                    progress_percentage
                ),
                "published_lesson_count": (
                    published_count
                ),
                "completed_lesson_count": (
                    completed_count
                ),
                "latest_attempt": latest_attempt,
                "certificate": certificate,
            }
        )

    enrollment_count = len(enrollment_rows)

    if total_lessons > 0:
        overall_progress = min(
            round(
                completed_lessons
                / total_lessons
                * 100
            ),
            100,
        )

    elif (
        enrollment_count > 0
        and completed_courses == enrollment_count
    ):
        overall_progress = 100

    else:
        overall_progress = 0

    context = {
        "school": school,
        "student": student,
        "enrollment_rows": enrollment_rows,
        "enrollment_count": enrollment_count,
        "completed_courses": completed_courses,
        "certificate_count": certificate_count,
        "total_lessons": total_lessons,
        "completed_lessons": completed_lessons,
        "overall_progress": overall_progress,
    }

    return render(
        request,
        "schools/student_detail.html",
        context,
    )

@school_administrator_required
def certificate_list(request):
    """
    Display certificates issued through the
    administrator's school.
    """

    school = request.school

    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    certificates = (
        Certificate.objects
        .filter(
            enrollment__school=school,
        )
        .select_related(
            "enrollment",
            "enrollment__user",
            "enrollment__course",
            "assessment_attempt",
            "assessment_attempt__assessment",
        )
    )

    if search_query:
        certificates = certificates.filter(
            Q(
                certificate_number__icontains=search_query,
            )
            | Q(
                enrollment__user__first_name__icontains=search_query,
            )
            | Q(
                enrollment__user__last_name__icontains=search_query,
            )
            | Q(
                enrollment__user__username__icontains=search_query,
            )
            | Q(
                enrollment__user__email__icontains=search_query,
            )
            | Q(
                enrollment__course__title__icontains=search_query,
            )
        )

    certificates = certificates.order_by(
        "-issued_at",
    )

    context = {
        "school": school,
        "certificates": certificates,
        "certificate_count": certificates.count(),
        "search_query": search_query,
    }

    return render(
        request,
        "schools/certificates.html",
        context,
    )


@school_administrator_required
def certificate_pdf(
    request,
    certificate_number,
):
    """
    Download a certificate only when its enrollment
    belongs to the administrator's school.
    """

    certificate = get_object_or_404(
        Certificate.objects.select_related(
            "enrollment",
            "enrollment__user",
            "enrollment__course",
            "assessment_attempt",
            "assessment_attempt__assessment",
        ),
        certificate_number=certificate_number,
        enrollment__school=request.school,
    )

    verification_url = request.build_absolute_uri(
        reverse(
            "courses:certificate_verify_code",
            kwargs={
                "verification_code": (
                    certificate.verification_code
                ),
            },
        )
    )

    pdf_buffer = build_certificate_pdf(
        certificate=certificate,
        verification_url=verification_url,
    )

    filename = (
        f"{certificate.certificate_number}.pdf"
    )

    return FileResponse(
        pdf_buffer,
        as_attachment=True,
        filename=filename,
        content_type="application/pdf",
    )