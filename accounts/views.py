from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import (
    Certificate,
    Enrollment,
    LessonProgress,
)


@login_required
def dashboard(request):
    enrollments = list(
        Enrollment.objects
        .filter(user=request.user)
        .select_related(
            "course",
            "course__category",
        )
        .order_by("-started_at")
    )

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

        total_lessons = len(
            published_lessons
        )

        completed_lessons = len(
            completed_lesson_ids
        )

        lessons_completed += (
            completed_lessons
        )

        if total_lessons > 0:
            progress_percentage = round(
                (
                    completed_lessons
                    / total_lessons
                )
                * 100
            )
        else:
            progress_percentage = 0

        next_lesson = None

        for lesson in published_lessons:
            if (
                lesson.id
                not in completed_lesson_ids
            ):
                next_lesson = lesson
                break

        if (
            next_lesson is None
            and published_lessons
        ):
            next_lesson = (
                published_lessons[-1]
            )

        enrollment.total_lessons = (
            total_lessons
        )

        enrollment.completed_lessons = (
            completed_lessons
        )

        enrollment.progress_percentage = (
            progress_percentage
        )

        enrollment.resume_lesson = (
            next_lesson
        )

        enrollment.certificate = (
            Certificate.objects
            .filter(
                enrollment=enrollment,
            )
            .first()
        )

        if enrollment.is_completed:
            courses_completed += 1

            completed_enrollments.append(
                enrollment
            )
        else:
            courses_started += 1

            in_progress_enrollments.append(
                enrollment
            )

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
        "courses_started": (
            courses_started
        ),
        "courses_completed": (
            courses_completed
        ),
        "lessons_completed": (
            lessons_completed
        ),
        "in_progress_enrollments": (
            in_progress_enrollments
        ),
        "completed_enrollments": (
            completed_enrollments
        ),
        "recent_activity": (
            recent_activity
        ),
    }

    return render(
        request,
        "accounts/dashboard.html",
        context,
    )