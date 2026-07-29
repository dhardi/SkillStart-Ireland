import random

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Max, Q
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import (
    AssessmentAttempt,
    AttemptQuestion,
    Enrollment,
    LessonProgress,
    StudentAnswer,
)

from .models import (
    Category,
    Course,
    CourseAssessment,
    Lesson,
)


def course_list(request):
    search_query = request.GET.get(
        "search",
        "",
    ).strip()

    selected_category = request.GET.get(
        "category",
        "",
    ).strip()

    courses = (
        Course.objects
        .filter(is_published=True)
        .select_related("category")
        .annotate(
            published_lesson_count=Count(
                "lessons",
                filter=Q(
                    lessons__is_published=True,
                ),
            ),
        )
        .order_by("title")
    )

    if search_query:
        courses = courses.filter(
            Q(
                title__icontains=search_query,
            )
            | Q(
                description__icontains=search_query,
            )
            | Q(
                category__name__icontains=search_query,
            )
        )

    if selected_category:
        courses = courses.filter(
            category__slug=selected_category,
        )

    categories = (
        Category.objects
        .filter(
            courses__is_published=True,
        )
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
        Course.objects.select_related(
            "category",
        ),
        slug=slug,
        is_published=True,
    )

    lessons = list(
        course.lessons
        .filter(
            is_published=True,
        )
        .order_by(
            "order",
            "id",
        )
    )

    course_button_text = "Start learning"
    course_button_lesson = None

    if lessons:
        course_button_lesson = lessons[0]

    if request.user.is_authenticated and lessons:
        enrollment = (
            Enrollment.objects
            .filter(
                user=request.user,
                course=course,
            )
            .first()
        )

        if enrollment:
            completed_lesson_ids = set(
                LessonProgress.objects
                .filter(
                    enrollment=enrollment,
                    completed=True,
                    lesson__course=course,
                    lesson__is_published=True,
                )
                .values_list(
                    "lesson_id",
                    flat=True,
                )
            )

            if completed_lesson_ids:
                first_incomplete_lesson = next(
                    (
                        course_lesson
                        for course_lesson in lessons
                        if course_lesson.id
                        not in completed_lesson_ids
                    ),
                    None,
                )

                if first_incomplete_lesson:
                    course_button_text = (
                        "Resume course"
                    )

                    course_button_lesson = (
                        first_incomplete_lesson
                    )
                else:
                    course_button_text = (
                        "Review lessons"
                    )

                    course_button_lesson = lessons[-1]

    assessment_available = (
        CourseAssessment.objects
        .filter(
            course=course,
            is_published=True,
        )
        .exists()
    )

    context = {
        "course": course,
        "lessons": lessons,
        "course_button_text": course_button_text,
        "course_button_lesson": course_button_lesson,
        "assessment_available": assessment_available,
    }

    return render(
        request,
        "courses/course_detail.html",
        context,
    )


def lesson_detail(
    request,
    course_slug,
    lesson_id,
):
    course = get_object_or_404(
        Course.objects.select_related(
            "category",
        ),
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
        .filter(
            is_published=True,
        )
        .order_by(
            "order",
            "id",
        )
    )

    current_position = published_lessons.index(
        lesson,
    )

    previous_lesson = None
    next_lesson = None

    if current_position > 0:
        previous_lesson = published_lessons[
            current_position - 1
        ]

    if (
        current_position
        < len(published_lessons) - 1
    ):
        next_lesson = published_lessons[
            current_position + 1
        ]

    completed_lesson_ids = []

    if request.user.is_authenticated:
        enrollment = (
            Enrollment.objects
            .filter(
                user=request.user,
                course=course,
            )
            .first()
        )

        if enrollment:
            completed_lesson_ids = list(
                LessonProgress.objects
                .filter(
                    enrollment=enrollment,
                    completed=True,
                    lesson__course=course,
                    lesson__is_published=True,
                )
                .values_list(
                    "lesson_id",
                    flat=True,
                )
            )

    completed_count = len(
        completed_lesson_ids,
    )

    total_lessons = len(
        published_lessons,
    )

    progress_percentage = (
        round(
            (
                completed_count
                / total_lessons
            )
            * 100,
        )
        if total_lessons > 0
        else 0
    )

    context = {
        "course": course,
        "lesson": lesson,
        "published_lessons": published_lessons,
        "current_position": (
            current_position + 1
        ),
        "previous_lesson": previous_lesson,
        "next_lesson": next_lesson,
        "completed_lesson_ids": (
            completed_lesson_ids
        ),
        "completed_count": completed_count,
        "total_lessons": total_lessons,
        "progress_percentage": (
            progress_percentage
        ),
        "current_lesson_completed": (
            lesson.id
            in completed_lesson_ids
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

        lesson_progress.completed_at = (
            timezone.now()
        )

        lesson_progress.save(
            update_fields=[
                "completed",
                "completed_at",
            ],
        )

    total_lessons = (
        course.lessons
        .filter(
            is_published=True,
        )
        .count()
    )

    completed_count = (
        LessonProgress.objects
        .filter(
            enrollment=enrollment,
            completed=True,
            lesson__course=course,
            lesson__is_published=True,
        )
        .count()
    )

    progress_percentage = (
        round(
            (
                completed_count
                / total_lessons
            )
            * 100,
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
                and completed_count
                == total_lessons
            ),
        },
    )


@login_required
def assessment_detail(
    request,
    course_slug,
):
    course = get_object_or_404(
        Course.objects.select_related(
            "category",
        ),
        slug=course_slug,
        is_published=True,
    )

    assessment = get_object_or_404(
        CourseAssessment,
        course=course,
        is_published=True,
    )

    enrollment = (
        Enrollment.objects
        .filter(
            user=request.user,
            course=course,
        )
        .first()
    )

    total_lessons = (
        course.lessons
        .filter(
            is_published=True,
        )
        .count()
    )

    completed_lessons = 0

    if enrollment:
        completed_lessons = (
            LessonProgress.objects
            .filter(
                enrollment=enrollment,
                completed=True,
                lesson__course=course,
                lesson__is_published=True,
            )
            .count()
        )

    lessons_completed = (
        total_lessons > 0
        and completed_lessons
        == total_lessons
    )

    attempts = (
        AssessmentAttempt.objects
        .filter(
            enrollment=enrollment,
            assessment=assessment,
        )
        .order_by(
            "-attempt_number",
        )
        if enrollment
        else AssessmentAttempt.objects.none()
    )

    completed_attempts_count = (
        attempts
        .filter(
            is_completed=True,
        )
        .count()
    )

    in_progress_attempt = (
        attempts
        .filter(
            is_completed=False,
        )
        .first()
    )

    attempts_remaining = None

    if assessment.maximum_attempts is not None:
        attempts_remaining = max(
            assessment.maximum_attempts
            - completed_attempts_count,
            0,
        )

    maximum_attempts_reached = (
        assessment.maximum_attempts
        is not None
        and completed_attempts_count
        >= assessment.maximum_attempts
        and in_progress_attempt is None
    )

    can_start = (
        enrollment is not None
        and lessons_completed
        and assessment.is_ready
        and not maximum_attempts_reached
    )

    context = {
        "course": course,
        "assessment": assessment,
        "enrollment": enrollment,
        "total_lessons": total_lessons,
        "completed_lessons": completed_lessons,
        "lessons_completed": lessons_completed,
        "completed_attempts_count": (
            completed_attempts_count
        ),
        "in_progress_attempt": (
            in_progress_attempt
        ),
        "attempts_remaining": attempts_remaining,
        "maximum_attempts_reached": (
            maximum_attempts_reached
        ),
        "can_start": can_start,
    }

    return render(
        request,
        "courses/assessment_detail.html",
        context,
    )


@login_required
@require_POST
@transaction.atomic
def start_assessment(
    request,
    course_slug,
):
    course = get_object_or_404(
        Course,
        slug=course_slug,
        is_published=True,
    )

    assessment = get_object_or_404(
        CourseAssessment,
        course=course,
        is_published=True,
    )

    enrollment = get_object_or_404(
        Enrollment.objects.select_for_update(),
        user=request.user,
        course=course,
    )

    in_progress_attempt = (
        AssessmentAttempt.objects
        .filter(
            enrollment=enrollment,
            assessment=assessment,
            is_completed=False,
        )
        .order_by(
            "-attempt_number",
        )
        .first()
    )

    if in_progress_attempt:
        first_unanswered = (
            in_progress_attempt
            .attempt_questions
            .filter(
                student_answer__isnull=True,
            )
            .order_by(
                "position",
            )
            .first()
        )

        position = (
            first_unanswered.position
            if first_unanswered
            else 1
        )

        return redirect(
            "courses:assessment_attempt",
            course_slug=course.slug,
            attempt_id=in_progress_attempt.id,
            position=position,
        )

    total_lessons = (
        course.lessons
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
            lesson__course=course,
            lesson__is_published=True,
        )
        .count()
    )

    if (
        total_lessons == 0
        or completed_lessons
        != total_lessons
    ):
        messages.error(
            request,
            (
                "You must complete all published lessons "
                "before starting the final assessment."
            ),
        )

        return redirect(
            "courses:assessment_detail",
            course_slug=course.slug,
        )

    if not assessment.is_ready:
        messages.error(
            request,
            (
                "This assessment is not ready yet. "
                "Please contact the course administrator."
            ),
        )

        return redirect(
            "courses:assessment_detail",
            course_slug=course.slug,
        )

    completed_attempts_count = (
        AssessmentAttempt.objects
        .filter(
            enrollment=enrollment,
            assessment=assessment,
            is_completed=True,
        )
        .count()
    )

    if (
        assessment.maximum_attempts is not None
        and completed_attempts_count
        >= assessment.maximum_attempts
    ):
        messages.error(
            request,
            (
                "You have reached the maximum number "
                "of attempts for this assessment."
            ),
        )

        return redirect(
            "courses:assessment_detail",
            course_slug=course.slug,
        )

    eligible_questions = list(
        assessment.questions
        .filter(
            is_published=True,
        )
        .prefetch_related(
            "answer_options",
        )
        .order_by(
            "order",
            "id",
        )
    )

    eligible_questions = [
        question
        for question in eligible_questions
        if question.is_ready
    ]

    required_question_count = (
        assessment.questions_per_attempt
    )

    if (
        len(eligible_questions)
        < required_question_count
    ):
        messages.error(
            request,
            (
                "There are not enough valid questions "
                "to start this assessment."
            ),
        )

        return redirect(
            "courses:assessment_detail",
            course_slug=course.slug,
        )

    if assessment.shuffle_questions:
        selected_questions = random.sample(
            eligible_questions,
            required_question_count,
        )
    else:
        selected_questions = (
            eligible_questions[
                :required_question_count
            ]
        )

    highest_attempt_number = (
        AssessmentAttempt.objects
        .filter(
            enrollment=enrollment,
            assessment=assessment,
        )
        .aggregate(
            highest=Max(
                "attempt_number",
            ),
        )
        .get("highest")
        or 0
    )

    attempt = AssessmentAttempt.objects.create(
        enrollment=enrollment,
        assessment=assessment,
        attempt_number=(
            highest_attempt_number + 1
        ),
        total_questions=required_question_count,
    )

    for position, question in enumerate(
        selected_questions,
        start=1,
    ):
        AttemptQuestion.objects.create(
            attempt=attempt,
            question=question,
            position=position,
        )

    messages.success(
        request,
        (
            f"Assessment attempt "
            f"{attempt.attempt_number} started."
        ),
    )

    return redirect(
        "courses:assessment_attempt",
        course_slug=course.slug,
        attempt_id=attempt.id,
        position=1,
    )


@login_required
def assessment_attempt(
    request,
    course_slug,
    attempt_id,
    position,
):
    course = get_object_or_404(
        Course,
        slug=course_slug,
        is_published=True,
    )

    attempt = get_object_or_404(
        AssessmentAttempt.objects.select_related(
            "assessment",
            "enrollment",
            "enrollment__user",
            "enrollment__course",
        ),
        id=attempt_id,
        enrollment__user=request.user,
        enrollment__course=course,
    )

    if attempt.is_completed:
        return redirect(
            "courses:assessment_result",
            course_slug=course.slug,
            attempt_id=attempt.id,
        )

    attempt_question = get_object_or_404(
        AttemptQuestion.objects
        .select_related(
            "question",
            "attempt",
        )
        .prefetch_related(
            "question__answer_options",
        ),
        attempt=attempt,
        position=position,
    )

    answer_options = list(
        attempt_question
        .question
        .answer_options
        .all()
        .order_by(
            "order",
            "id",
        )
    )

    if attempt.assessment.shuffle_answers:
        random_generator = random.Random(
            f"{attempt.id}-{attempt_question.id}",
        )

        random_generator.shuffle(
            answer_options,
        )

    if request.method == "POST":
        selected_option_id = request.POST.get(
            "selected_option",
        )

        if not selected_option_id:
            messages.error(
                request,
                "Please select an answer before continuing.",
            )

            return redirect(
                "courses:assessment_attempt",
                course_slug=course.slug,
                attempt_id=attempt.id,
                position=position,
            )

        selected_option = get_object_or_404(
            attempt_question.question.answer_options,
            id=selected_option_id,
        )

        with transaction.atomic():
            StudentAnswer.objects.update_or_create(
                attempt_question=attempt_question,
                defaults={
                    "selected_option": selected_option,
                },
            )

        if position < attempt.total_questions:
            return redirect(
                "courses:assessment_attempt",
                course_slug=course.slug,
                attempt_id=attempt.id,
                position=position + 1,
            )

        first_unanswered_question = (
            attempt
            .attempt_questions
            .filter(
                student_answer__isnull=True,
            )
            .order_by(
                "position",
            )
            .first()
        )

        if first_unanswered_question:
            messages.warning(
                request,
                (
                    "You still have unanswered questions. "
                    "Complete them before finishing the assessment."
                ),
            )

            return redirect(
                "courses:assessment_attempt",
                course_slug=course.slug,
                attempt_id=attempt.id,
                position=first_unanswered_question.position,
            )

        try:
            attempt.calculate_result()
        except ValidationError as error:
            messages.error(
                request,
                " ".join(error.messages),
            )

            return redirect(
                "courses:assessment_attempt",
                course_slug=course.slug,
                attempt_id=attempt.id,
                position=position,
            )

        return redirect(
            "courses:assessment_result",
            course_slug=course.slug,
            attempt_id=attempt.id,
        )

    existing_answer = getattr(
        attempt_question,
        "student_answer",
        None,
    )

    previous_position = (
        position - 1
        if position > 1
        else None
    )

    next_position = (
        position + 1
        if position < attempt.total_questions
        else None
    )

    answered_count = (
        attempt.answered_question_count
    )

    progress_percentage = (
        round(
            answered_count
            / attempt.total_questions
            * 100,
        )
        if attempt.total_questions > 0
        else 0
    )

    context = {
        "course": course,
        "assessment": attempt.assessment,
        "attempt": attempt,
        "attempt_question": attempt_question,
        "question": attempt_question.question,
        "answer_options": answer_options,
        "existing_answer": existing_answer,
        "position": position,
        "previous_position": previous_position,
        "next_position": next_position,
        "answered_count": answered_count,
        "progress_percentage": progress_percentage,
    }

    return render(
        request,
        "courses/assessment_attempt.html",
        context,
    )

@login_required
def assessment_result(
    request,
    course_slug,
    attempt_id,
):
    course = get_object_or_404(
        Course,
        slug=course_slug,
        is_published=True,
    )

    attempt = get_object_or_404(
        AssessmentAttempt.objects.select_related(
            "assessment",
            "enrollment",
            "enrollment__user",
            "enrollment__course",
        ),
        id=attempt_id,
        enrollment__user=request.user,
        enrollment__course=course,
        is_completed=True,
    )

    answers = (
        StudentAnswer.objects
        .filter(
            attempt_question__attempt=attempt,
        )
        .select_related(
            "attempt_question",
            "attempt_question__question",
            "selected_option",
        )
        .order_by(
            "attempt_question__position",
        )
    )

    context = {
        "course": course,
        "assessment": attempt.assessment,
        "attempt": attempt,
        "answers": answers,
    }

    return render(
        request,
        "courses/assessment_result.html",
        context,
    )