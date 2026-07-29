from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from .models import (
    AnswerOption,
    Category,
    Course,
    CourseAssessment,
    Lesson,
    Question,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
    )

    search_fields = (
        "name",
    )

    prepopulated_fields = {
        "slug": (
            "name",
        ),
    }


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1

    fields = (
        "title",
        "order",
        "is_published",
        "content",
    )

    ordering = (
        "order",
    )


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "is_published",
        "created_at",
    )

    list_filter = (
        "category",
        "is_published",
    )

    search_fields = (
        "title",
        "description",
    )

    prepopulated_fields = {
        "slug": (
            "title",
        ),
    }

    inlines = [
        LessonInline,
    ]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "course",
        "order",
        "is_published",
    )

    list_filter = (
        "course",
        "is_published",
    )

    search_fields = (
        "title",
        "content",
    )

    ordering = (
        "course",
        "order",
    )


class AnswerOptionInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        if any(self.errors):
            return

        active_answers = []
        correct_answers = []

        for form in self.forms:
            cleaned_data = getattr(
                form,
                "cleaned_data",
                None,
            )

            if not cleaned_data:
                continue

            if cleaned_data.get("DELETE"):
                continue

            answer_text = cleaned_data.get("text")

            if not answer_text:
                continue

            active_answers.append(form)

            if cleaned_data.get("is_correct"):
                correct_answers.append(form)

        if len(active_answers) != 4:
            raise ValidationError(
                "Each question must have exactly four answer options."
            )

        if len(correct_answers) != 1:
            raise ValidationError(
                "Each question must have exactly one correct answer."
            )


class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    formset = AnswerOptionInlineFormSet

    extra = 4
    min_num = 4
    max_num = 4

    validate_min = True
    validate_max = True

    fields = (
        "order",
        "text",
        "is_correct",
    )

    ordering = (
        "order",
    )

    verbose_name = "Answer option"
    verbose_name_plural = "Answer options — exactly four required"


@admin.register(CourseAssessment)
class CourseAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "course",
        "passing_score",
        "questions_per_attempt",
        "required_correct_answers_display",
        "published_question_count_display",
        "ready_status",
        "is_published",
    )

    list_filter = (
        "is_published",
        "passing_score",
        "shuffle_questions",
        "shuffle_answers",
    )

    search_fields = (
        "title",
        "course__title",
        "instructions",
    )

    readonly_fields = (
        "required_correct_answers_display",
        "published_question_count_display",
        "ready_status",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Assessment information",
            {
                "fields": (
                    "course",
                    "title",
                    "instructions",
                ),
            },
        ),
        (
            "Passing rules",
            {
                "fields": (
                    "passing_score",
                    "questions_per_attempt",
                    "maximum_attempts",
                    "required_correct_answers_display",
                ),
            },
        ),
        (
            "Question settings",
            {
                "fields": (
                    "shuffle_questions",
                    "shuffle_answers",
                ),
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "is_published",
                    "published_question_count_display",
                    "ready_status",
                ),
            },
        ),
        (
            "Dates",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
    )

    ordering = (
        "course__title",
    )

    @admin.display(
        description="Required correct answers",
    )
    def required_correct_answers_display(self, obj):
        if not obj:
            return "-"

        return (
            f"{obj.required_correct_answers} "
            f"of {obj.questions_per_attempt}"
        )

    @admin.display(
        description="Published questions",
    )
    def published_question_count_display(self, obj):
        if not obj or not obj.pk:
            return 0

        return obj.published_question_count

    @admin.display(
        boolean=True,
        description="Ready",
    )
    def ready_status(self, obj):
        if not obj or not obj.pk:
            return False

        return obj.is_ready


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        "question_number",
        "assessment",
        "short_question_text",
        "answer_count",
        "correct_answer_display",
        "ready_status",
        "is_published",
    )

    list_filter = (
        "assessment",
        "is_published",
    )

    search_fields = (
        "text",
        "explanation",
        "assessment__title",
        "assessment__course__title",
    )

    ordering = (
        "assessment",
        "order",
    )

    readonly_fields = (
        "answer_count",
        "correct_answer_display",
        "ready_status",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Question",
            {
                "fields": (
                    "assessment",
                    "order",
                    "text",
                    "explanation",
                    "is_published",
                ),
            },
        ),
        (
            "Validation",
            {
                "fields": (
                    "answer_count",
                    "correct_answer_display",
                    "ready_status",
                ),
            },
        ),
        (
            "Dates",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
    )

    inlines = [
        AnswerOptionInline,
    ]

    @admin.display(
        description="Question",
        ordering="order",
    )
    def question_number(self, obj):
        return f"Question {obj.order}"

    @admin.display(
        description="Question text",
    )
    def short_question_text(self, obj):
        maximum_length = 80

        if len(obj.text) <= maximum_length:
            return obj.text

        return f"{obj.text[:maximum_length]}..."

    @admin.display(
        description="Answers",
    )
    def answer_count(self, obj):
        if not obj or not obj.pk:
            return 0

        return obj.answer_options.count()

    @admin.display(
        description="Correct answer",
    )
    def correct_answer_display(self, obj):
        if not obj or not obj.pk:
            return "Not defined"

        correct_answer = obj.correct_answer

        if not correct_answer:
            return "Not defined"

        return (
            f"Answer {correct_answer.order}: "
            f"{correct_answer.text}"
        )

    @admin.display(
        boolean=True,
        description="Ready",
    )
    def ready_status(self, obj):
        if not obj or not obj.pk:
            return False

        return obj.is_ready


@admin.register(AnswerOption)
class AnswerOptionAdmin(admin.ModelAdmin):
    list_display = (
        "text",
        "question",
        "order",
        "is_correct",
    )

    list_filter = (
        "is_correct",
        "question__assessment",
    )

    search_fields = (
        "text",
        "question__text",
        "question__assessment__course__title",
    )

    ordering = (
        "question",
        "order",
    )

    list_select_related = (
        "question",
        "question__assessment",
        "question__assessment__course",
    )