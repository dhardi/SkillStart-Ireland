from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import (
    StudentProfileForm,
    StudentRegistrationForm,
    UserProfileForm,
)

from .models import (
    Certificate,
    Enrollment,
    LessonProgress,
    StudentProfile,
)


def register(request):
    """
    Create a new student account and sign the student in automatically.
    """

    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    if request.method == "POST":
        form = StudentRegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()

            login(
                request,
                user,
            )

            return redirect(
                "accounts:dashboard"
            )

    else:
        form = StudentRegistrationForm()

    context = {
        "form": form,
    }

    return render(
        request,
        "accounts/register.html",
        context,
    )

@login_required
def profile(request):
    """
    Display and update the logged-in student's profile.
    """

    student_profile, created = (
        StudentProfile.objects.get_or_create(
            user=request.user,
        )
    )

    if request.method == "POST":
        user_form = UserProfileForm(
            request.POST,
            instance=request.user,
        )

        profile_form = StudentProfileForm(
            request.POST,
            request.FILES,
            instance=student_profile,
        )

        if (
            user_form.is_valid()
            and profile_form.is_valid()
        ):
            user_form.save()
            profile_form.save()

            messages.success(
                request,
                "Your profile has been updated successfully.",
            )

            return redirect(
                "accounts:profile"
            )

    else:
        user_form = UserProfileForm(
            instance=request.user,
        )

        profile_form = StudentProfileForm(
            instance=student_profile,
        )

    courses_enrolled = (
        Enrollment.objects
        .filter(user=request.user)
        .count()
    )

    courses_completed = (
        Enrollment.objects
        .filter(
            user=request.user,
            is_completed=True,
        )
        .count()
    )

    lessons_completed = (
        LessonProgress.objects
        .filter(
            enrollment__user=request.user,
            completed=True,
        )
        .count()
    )

    certificate_count = (
        Certificate.objects
        .filter(
            enrollment__user=request.user,
        )
        .count()
    )

    context = {
        "student_profile": student_profile,
        "user_form": user_form,
        "profile_form": profile_form,
        "courses_enrolled": courses_enrolled,
        "courses_completed": courses_completed,
        "lessons_completed": lessons_completed,
        "certificate_count": certificate_count,
    }

    return render(
        request,
        "accounts/profile.html",
        context,
    )

@login_required
def dashboard(request):
    """
    Display the logged-in student's dashboard.

    The dashboard contains:
    - Courses in progress
    - Completed courses
    - Lesson progress
    - Recent activity
    - Certificates earned by the student
    """

    enrollments = list(
        Enrollment.objects
        .filter(user=request.user)
        .select_related(
            "course",
            "course__category",
        )
        .order_by("-started_at")
    )

    # Load all certificates belonging to the logged-in student.
    certificates = list(
        Certificate.objects
        .filter(
            enrollment__user=request.user,
        )
        .select_related(
            "enrollment",
            "enrollment__course",
            "assessment_attempt",
            "assessment_attempt__assessment",
        )
        .order_by("-issued_at")
    )

    # Connect each certificate to its enrollment without
    # performing a new query for every course.
    certificates_by_enrollment_id = {
        certificate.enrollment_id: certificate
        for certificate in certificates
    }

    courses_started = 0
    courses_completed = 0
    lessons_completed = 0

    in_progress_enrollments = []
    completed_enrollments = []

    for enrollment in enrollments:
        published_lessons = list(
            enrollment.course.lessons
            .filter(is_published=True)
            .order_by("order", "id")
        )

        completed_lesson_ids = set(
            LessonProgress.objects
            .filter(
                enrollment=enrollment,
                completed=True,
                lesson__course=enrollment.course,
                lesson__is_published=True,
            )
            .values_list(
                "lesson_id",
                flat=True,
            )
        )

        total_lessons = len(published_lessons)
        completed_lessons_count = len(completed_lesson_ids)

        lessons_completed += completed_lessons_count

        if total_lessons > 0:
            progress_percentage = round(
                (
                    completed_lessons_count
                    / total_lessons
                )
                * 100
            )
        else:
            progress_percentage = 0

        resume_lesson = None

        for lesson in published_lessons:
            if lesson.id not in completed_lesson_ids:
                resume_lesson = lesson
                break

        # If all lessons are complete, use the last lesson
        # so the course can still be reviewed.
        if resume_lesson is None and published_lessons:
            resume_lesson = published_lessons[-1]

        # These attribute names must match dashboard.html.
        enrollment.total_lessons = total_lessons
        enrollment.completed_lessons = completed_lessons_count
        enrollment.progress_percentage = progress_percentage
        enrollment.resume_lesson = resume_lesson

        enrollment.certificate = (
            certificates_by_enrollment_id.get(
                enrollment.id
            )
        )

        if enrollment.is_completed:
            courses_completed += 1
            completed_enrollments.append(enrollment)
        else:
            courses_started += 1
            in_progress_enrollments.append(enrollment)

    # Keep recent_activity as LessonProgress objects.
    # dashboard.html accesses:
    # progress.lesson.course.slug
    # progress.lesson.id
    recent_activity = (
        LessonProgress.objects
        .filter(
            enrollment__user=request.user,
            completed=True,
            completed_at__isnull=False,
        )
        .select_related(
            "lesson",
            "lesson__course",
        )
        .order_by("-completed_at")[:5]
    )

    context = {
        "courses_started": courses_started,
        "courses_completed": courses_completed,
        "lessons_completed": lessons_completed,
        "in_progress_enrollments": in_progress_enrollments,
        "completed_enrollments": completed_enrollments,
        "recent_activity": recent_activity,
        "certificates": certificates,
        "certificate_count": len(certificates),
    }

    return render(
        request,
        "accounts/dashboard.html",
        context,
    )