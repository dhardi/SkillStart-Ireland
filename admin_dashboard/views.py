from django.contrib.admin.views.decorators import (
    staff_member_required,
)
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.shortcuts import render

from accounts.models import Enrollment, LessonProgress
from courses.models import Category, Course, Lesson


User = get_user_model()


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