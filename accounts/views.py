from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Enrollment


@login_required
def dashboard(request):
    enrollments = (
        Enrollment.objects
        .filter(user=request.user)
        .select_related("course")
    )

    courses_started = enrollments.filter(
        is_completed=False,
    ).count()

    courses_completed = enrollments.filter(
        is_completed=True,
    ).count()

    context = {
        "enrollments": enrollments,
        "courses_started": courses_started,
        "courses_completed": courses_completed,
        "lessons_completed": 0,
    }

    return render(
        request,
        "accounts/dashboard.html",
        context,
    )