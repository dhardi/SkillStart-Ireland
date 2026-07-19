from django.shortcuts import get_object_or_404, render

from .models import Course


def course_list(request):
    courses = Course.objects.filter(is_published=True)

    context = {
        "courses": courses,
    }

    return render(request, "courses/course_list.html", context)


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

    return render(request, "courses/course_detail.html", context)