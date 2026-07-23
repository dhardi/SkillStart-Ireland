from .models import Category, Course, Lesson
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from .models import Category, Course


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
        .order_by("order")
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
        previous_lesson = published_lessons[current_position - 1]

    if current_position < len(published_lessons) - 1:
        next_lesson = published_lessons[current_position + 1]

    context = {
        "course": course,
        "lesson": lesson,
        "published_lessons": published_lessons,
        "current_position": current_position + 1,
        "previous_lesson": previous_lesson,
        "next_lesson": next_lesson,
    }

    return render(
        request,
        "courses/lesson_detail.html",
        context,
    )