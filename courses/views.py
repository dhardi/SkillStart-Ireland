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