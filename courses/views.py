from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import Enrollment, LessonProgress

from .models import Category, Course, Lesson


def course_list(request):
    search_query = request.GET.get("search", "").strip()
    selected_category = request.GET.get("category", "").strip()

    courses = (
        Course.objects
        .filter(is_published=True)
        .select_related("category")
        .annotate(
            published_lesson_count=Count(
                "lessons",
                filter=Q(lessons__is_published=True),
            )
        )
        .order_by("title")
    )

    if search_query:
        courses = courses.filter(
            Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(category__name__icontains=search_query)
        )

    if selected_category:
        courses = courses.filter(
            category__slug=selected_category
        )

    categories = (
        Category.objects
        .filter(courses__is_published=True)
        .distinct()
        .order_by("name")
    )

    context = {
        "courses": courses,
        "categories": categories,
        "search_query": search_query,
        "selected_category": selected_category,
    }

    return render(
        request,
        "courses/course_list.html",
        context,
    )


def course_detail(request, slug):
    course = get_object_or_404(
        Course,
        slug=slug,
        is_published=True,
    )

    lessons = (
        course.lessons
        .filter(is_published=True)
        .order_by("order", "id")
    )

    context = {
        "course": course,
        "lessons": lessons,
    }

    return render(
        request,
        "courses/course_detail.html",
        context,
    )


def lesson_detail(request, course_slug, lesson_id):
    course = get_object_or_404(
        Course.objects.select_related("category"),
        slug=course_slug,
        is_published=True,
    )

    lesson = get_object_or_404(
        Lesson,
        id=lesson_id,
        course=course,
        is_published=True,
    )

    published_lessons = list(
        course.lessons
        .filter(is_published=True)
        .order_by("order", "id")
    )

    current_position = published_lessons.index(lesson)

    previous_lesson = None
    next_lesson = None

    if current_position > 0:
        previous_lesson = published_lessons[
            current_position - 1
        ]

    if current_position < len(published_lessons) - 1:
        next_lesson = published_lessons[
            current_position + 1
        ]

    completed_lesson_ids = []

    if request.user.is_authenticated:
        enrollment = Enrollment.objects.filter(
            user=request.user,
            course=course,
        ).first()

        if enrollment:
            completed_lesson_ids = list(
                LessonProgress.objects.filter(
                    enrollment=enrollment,
                    completed=True,
                    lesson__course=course,
                    lesson__is_published=True,
                ).values_list(
                    "lesson_id",
                    flat=True,
                )
            )

    completed_count = len(completed_lesson_ids)
    total_lessons = len(published_lessons)

    progress_percentage = (
        round(
            (completed_count / total_lessons) * 100
        )
        if total_lessons > 0
        else 0
    )

    context = {
        "course": course,
        "lesson": lesson,
        "published_lessons": published_lessons,
        "current_position": current_position + 1,
        "previous_lesson": previous_lesson,
        "next_lesson": next_lesson,
        "completed_lesson_ids": completed_lesson_ids,
        "completed_count": completed_count,
        "total_lessons": total_lessons,
        "progress_percentage": progress_percentage,
        "current_lesson_completed": (
            lesson.id in completed_lesson_ids
        ),
    }

    return render(
        request,
        "courses/lesson_detail.html",
        context,
    )


@login_required
@require_POST
def mark_lesson_completed(
    request,
    course_slug,
    lesson_id,
):
    course = get_object_or_404(
        Course,
        slug=course_slug,
        is_published=True,
    )

    lesson = get_object_or_404(
        Lesson,
        id=lesson_id,
        course=course,
        is_published=True,
    )

    enrollment, enrollment_created = (
        Enrollment.objects.get_or_create(
            user=request.user,
            course=course,
        )
    )

    lesson_progress, progress_created = (
        LessonProgress.objects.get_or_create(
            enrollment=enrollment,
            lesson=lesson,
        )
    )

    if not lesson_progress.completed:
        lesson_progress.completed = True
        lesson_progress.completed_at = timezone.now()

        lesson_progress.save(
            update_fields=[
                "completed",
                "completed_at",
            ]
        )

    total_lessons = course.lessons.filter(
        is_published=True,
    ).count()

    completed_count = LessonProgress.objects.filter(
        enrollment=enrollment,
        completed=True,
        lesson__course=course,
        lesson__is_published=True,
    ).count()

    progress_percentage = (
        round(
            (completed_count / total_lessons) * 100
        )
        if total_lessons > 0
        else 0
    )

    return JsonResponse(
        {
            "success": True,
            "lesson_id": lesson.id,
            "completed_count": completed_count,
            "total_lessons": total_lessons,
            "percentage": progress_percentage,
            "all_lessons_completed": (
                total_lessons > 0
                and completed_count == total_lessons
            ),
        }
    )