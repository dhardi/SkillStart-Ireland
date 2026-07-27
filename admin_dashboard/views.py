from django.contrib.admin.views.decorators import (
    staff_member_required,
)
from .forms import EnrollmentForm
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.contrib import messages
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

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