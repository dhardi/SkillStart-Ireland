from django.contrib import admin

from .models import (
    AssessmentAttempt,
    AttemptQuestion,
    Enrollment,
    LessonProgress,
    StudentAnswer,
    StudentProfile,
)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "course",
        "started_at",
        "is_completed",
        "completed_at",
    )

    list_filter = (
        "is_completed",
        "started_at",
        "course",
    )

    search_fields = (
        "user__username",
        "user__email",
        "course__title",
    )

    readonly_fields = (
        "started_at",
        "completed_at",
    )

    autocomplete_fields = (
        "user",
        "course",
    )

    ordering = (
        "-started_at",
    )


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = (
        "enrollment",
        "lesson",
        "completed",
        "completed_at",
    )

    list_filter = (
        "completed",
        "lesson__course",
    )

    search_fields = (
        "lesson__title",
        "enrollment__user__username",
        "enrollment__course__title",
    )

    autocomplete_fields = (
        "enrollment",
        "lesson",
    )

    readonly_fields = (
        "completed_at",
    )

    ordering = (
        "lesson__course",
        "lesson__order",
    )


class AttemptQuestionInline(admin.TabularInline):
    model = AttemptQuestion

    extra = 0

    fields = (
        "position",
        "question",
        "answer_status",
    )

    readonly_fields = (
        "position",
        "question",
        "answer_status",
    )

    can_delete = False
    show_change_link = True

    ordering = (
        "position",
    )

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(
        description="Answer status",
    )
    def answer_status(self, obj):
        if not obj or not obj.pk:
            return "-"

        if not hasattr(obj, "student_answer"):
            return "Not answered"

        if obj.student_answer.is_correct:
            return "Correct"

        return "Incorrect"


@admin.register(AssessmentAttempt)
class AssessmentAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "course",
        "assessment",
        "attempt_number",
        "result_display",
        "score_percentage",
        "is_passed",
        "is_completed",
        "started_at",
        "completed_at",
    )

    list_filter = (
        "is_passed",
        "is_completed",
        "assessment",
        "started_at",
    )

    search_fields = (
        "enrollment__user__username",
        "enrollment__user__email",
        "enrollment__course__title",
        "assessment__title",
    )

    readonly_fields = (
        "enrollment",
        "assessment",
        "attempt_number",
        "total_questions",
        "correct_answers",
        "score_percentage",
        "is_passed",
        "is_completed",
        "started_at",
        "completed_at",
        "answered_question_count_display",
        "required_correct_answers_display",
    )

    fieldsets = (
        (
            "Attempt information",
            {
                "fields": (
                    "enrollment",
                    "assessment",
                    "attempt_number",
                ),
            },
        ),
        (
            "Assessment result",
            {
                "fields": (
                    "total_questions",
                    "answered_question_count_display",
                    "correct_answers",
                    "required_correct_answers_display",
                    "score_percentage",
                    "is_passed",
                    "is_completed",
                ),
            },
        ),
        (
            "Dates",
            {
                "fields": (
                    "started_at",
                    "completed_at",
                ),
            },
        ),
    )

    inlines = (
        AttemptQuestionInline,
    )

    list_select_related = (
        "enrollment",
        "enrollment__user",
        "enrollment__course",
        "assessment",
    )

    ordering = (
        "-started_at",
    )

    date_hierarchy = "started_at"

    @admin.display(
        description="Student",
        ordering="enrollment__user__username",
    )
    def student(self, obj):
        return obj.enrollment.user

    @admin.display(
        description="Course",
        ordering="enrollment__course__title",
    )
    def course(self, obj):
        return obj.enrollment.course

    @admin.display(
        description="Result",
    )
    def result_display(self, obj):
        if not obj.is_completed:
            return "In progress"

        return (
            f"{obj.correct_answers} / "
            f"{obj.total_questions}"
        )

    @admin.display(
        description="Answered questions",
    )
    def answered_question_count_display(self, obj):
        if not obj or not obj.pk:
            return 0

        return (
            f"{obj.answered_question_count} / "
            f"{obj.total_questions}"
        )

    @admin.display(
        description="Required correct answers",
    )
    def required_correct_answers_display(self, obj):
        if not obj or not obj.pk:
            return 0

        return obj.required_correct_answers

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_completed:
            return False

        return super().has_delete_permission(
            request,
            obj,
        )


@admin.register(AttemptQuestion)
class AttemptQuestionAdmin(admin.ModelAdmin):
    list_display = (
        "attempt",
        "position",
        "question",
        "answer_status",
    )

    list_filter = (
        "attempt__assessment",
    )

    search_fields = (
        "attempt__enrollment__user__username",
        "attempt__enrollment__user__email",
        "attempt__assessment__title",
        "question__text",
    )

    readonly_fields = (
        "attempt",
        "question",
        "position",
        "answer_status",
    )

    list_select_related = (
        "attempt",
        "attempt__assessment",
        "attempt__enrollment",
        "attempt__enrollment__user",
        "question",
    )

    ordering = (
        "-attempt__started_at",
        "position",
    )

    @admin.display(
        description="Answer status",
    )
    def answer_status(self, obj):
        if not hasattr(obj, "student_answer"):
            return "Not answered"

        if obj.student_answer.is_correct:
            return "Correct"

        return "Incorrect"

    def has_add_permission(self, request):
        return False

    def has_change_permission(
        self,
        request,
        obj=None,
    ):
        if obj:
            return False

        return super().has_change_permission(
            request,
            obj,
        )

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        if obj and obj.attempt.is_completed:
            return False

        return super().has_delete_permission(
            request,
            obj,
        )


@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "assessment",
        "question_number",
        "selected_option",
        "is_correct",
        "answered_at",
    )

    list_filter = (
        "is_correct",
        "attempt_question__attempt__assessment",
        "answered_at",
    )

    search_fields = (
        "attempt_question__attempt__enrollment__user__username",
        "attempt_question__attempt__enrollment__user__email",
        "attempt_question__question__text",
        "selected_option__text",
        "attempt_question__attempt__assessment__title",
    )

    readonly_fields = (
        "attempt_question",
        "selected_option",
        "is_correct",
        "answered_at",
    )

    list_select_related = (
        "attempt_question",
        "attempt_question__attempt",
        "attempt_question__attempt__enrollment",
        "attempt_question__attempt__enrollment__user",
        "attempt_question__attempt__assessment",
        "attempt_question__question",
        "selected_option",
    )

    ordering = (
        "-answered_at",
    )

    @admin.display(
        description="Student",
        ordering=(
            "attempt_question__attempt__enrollment__user__username"
        ),
    )
    def student(self, obj):
        return (
            obj.attempt_question
            .attempt
            .enrollment
            .user
        )

    @admin.display(
        description="Assessment",
        ordering=(
            "attempt_question__attempt__assessment__title"
        ),
    )
    def assessment(self, obj):
        return obj.attempt_question.attempt.assessment

    @admin.display(
        description="Question",
        ordering="attempt_question__position",
    )
    def question_number(self, obj):
        return (
            f"Question "
            f"{obj.attempt_question.position}"
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(
        self,
        request,
        obj=None,
    ):
        if obj:
            return False

        return super().has_change_permission(
            request,
            obj,
        )

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        if (
            obj
            and obj.attempt_question.attempt.is_completed
        ):
            return False

        return super().has_delete_permission(
            request,
            obj,
        )


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "phone_number",
        "preferred_language",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "preferred_language",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
        "phone_number",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    autocomplete_fields = (
        "user",
    )