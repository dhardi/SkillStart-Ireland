from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from courses.models import (
    AnswerOption,
    Course,
    CourseAssessment,
    Lesson,
    Question,
)


class Enrollment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )

    started_at = models.DateTimeField(
        auto_now_add=True,
    )

    completed_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    is_completed = models.BooleanField(
        default=False,
    )

    class Meta:
        ordering = ["-started_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["user", "course"],
                name="unique_user_course_enrollment",
            ),
        ]

    def mark_as_completed(self):
        if self.is_completed:
            return

        self.is_completed = True
        self.completed_at = timezone.now()

        self.save(
            update_fields=[
                "is_completed",
                "completed_at",
            ],
        )

    def __str__(self):
        return f"{self.user.username} - {self.course.title}"


class LessonProgress(models.Model):
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="lesson_progress",
    )

    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="lesson_progress",
    )

    completed = models.BooleanField(
        default=False,
    )

    completed_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "lesson"],
                name="unique_enrollment_lesson",
            ),
        ]

    def clean(self):
        super().clean()

        if (
            self.enrollment_id
            and self.lesson_id
            and self.enrollment.course_id != self.lesson.course_id
        ):
            raise ValidationError(
                {
                    "lesson": (
                        "The selected lesson does not belong "
                        "to the enrollment course."
                    ),
                },
            )

    def __str__(self):
        return (
            f"{self.enrollment.user.username} - "
            f"{self.lesson.title}"
        )


class AssessmentAttempt(models.Model):
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="assessment_attempts",
    )

    assessment = models.ForeignKey(
        CourseAssessment,
        on_delete=models.CASCADE,
        related_name="attempts",
    )

    attempt_number = models.PositiveIntegerField(
        default=1,
    )

    total_questions = models.PositiveIntegerField(
        default=0,
    )

    correct_answers = models.PositiveIntegerField(
        default=0,
    )

    score_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    is_passed = models.BooleanField(
        default=False,
    )

    is_completed = models.BooleanField(
        default=False,
    )

    started_at = models.DateTimeField(
        auto_now_add=True,
    )

    completed_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        ordering = [
            "-started_at",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "enrollment",
                    "assessment",
                    "attempt_number",
                ],
                name="unique_assessment_attempt_number",
            ),
        ]

    def clean(self):
        super().clean()

        if not self.enrollment_id or not self.assessment_id:
            return

        if self.enrollment.course_id != self.assessment.course_id:
            raise ValidationError(
                {
                    "assessment": (
                        "This assessment does not belong "
                        "to the enrollment course."
                    ),
                },
            )

        if self.attempt_number < 1:
            raise ValidationError(
                {
                    "attempt_number": (
                        "The attempt number must be at least 1."
                    ),
                },
            )

        maximum_attempts = self.assessment.maximum_attempts

        if (
            maximum_attempts is not None
            and self.attempt_number > maximum_attempts
        ):
            raise ValidationError(
                {
                    "attempt_number": (
                        "The maximum number of attempts "
                        "for this assessment has been reached."
                    ),
                },
            )

        if self.correct_answers > self.total_questions:
            raise ValidationError(
                {
                    "correct_answers": (
                        "Correct answers cannot be greater "
                        "than the total number of questions."
                    ),
                },
            )

    @property
    def answered_question_count(self):
        if not self.pk:
            return 0

        return self.attempt_questions.filter(
            student_answer__isnull=False,
        ).count()

    @property
    def required_correct_answers(self):
        if self.total_questions < 1:
            return 0

        return (
            self.total_questions
            * self.assessment.passing_score
            + 99
        ) // 100

    @property
    def can_be_completed(self):
        return (
            self.total_questions > 0
            and self.answered_question_count
            == self.total_questions
        )

    @transaction.atomic
    def calculate_result(self):
        if self.is_completed:
            return

        answered_questions = self.attempt_questions.filter(
            student_answer__isnull=False,
        ).count()

        if answered_questions != self.total_questions:
            raise ValidationError(
                (
                    "The assessment cannot be completed until "
                    "all questions have been answered."
                ),
            )

        correct_answers = self.attempt_questions.filter(
            student_answer__is_correct=True,
        ).count()

        score = (
            Decimal(correct_answers)
            / Decimal(self.total_questions)
            * Decimal("100")
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        self.correct_answers = correct_answers
        self.score_percentage = score

        self.is_passed = score >= Decimal(
            str(self.assessment.passing_score),
        )

        self.is_completed = True
        self.completed_at = timezone.now()

        self.save(
            update_fields=[
                "correct_answers",
                "score_percentage",
                "is_passed",
                "is_completed",
                "completed_at",
            ],
        )

        if self.is_passed:
            self.enrollment.mark_as_completed()

    def save(self, *args, **kwargs):
        self.full_clean()

        return super().save(
            *args,
            **kwargs,
        )

    def __str__(self):
        return (
            f"{self.enrollment.user.username} - "
            f"{self.assessment.title} - "
            f"Attempt {self.attempt_number}"
        )


class AttemptQuestion(models.Model):
    attempt = models.ForeignKey(
        AssessmentAttempt,
        on_delete=models.CASCADE,
        related_name="attempt_questions",
    )

    question = models.ForeignKey(
        Question,
        on_delete=models.PROTECT,
        related_name="attempt_questions",
    )

    position = models.PositiveIntegerField()

    class Meta:
        ordering = [
            "position",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "attempt",
                    "question",
                ],
                name="unique_question_per_attempt",
            ),
            models.UniqueConstraint(
                fields=[
                    "attempt",
                    "position",
                ],
                name="unique_question_position_per_attempt",
            ),
        ]

    def clean(self):
        super().clean()

        if not self.attempt_id or not self.question_id:
            return

        if (
            self.question.assessment_id
            != self.attempt.assessment_id
        ):
            raise ValidationError(
                {
                    "question": (
                        "This question does not belong "
                        "to the attempt assessment."
                    ),
                },
            )

        if not self.question.is_published:
            raise ValidationError(
                {
                    "question": (
                        "An unpublished question cannot "
                        "be added to an attempt."
                    ),
                },
            )

        if not self.question.is_ready:
            raise ValidationError(
                {
                    "question": (
                        "The question must have exactly four "
                        "answers and one correct answer."
                    ),
                },
            )

        if self.position < 1:
            raise ValidationError(
                {
                    "position": (
                        "The question position must be at least 1."
                    ),
                },
            )

        if (
            self.attempt.total_questions > 0
            and self.position > self.attempt.total_questions
        ):
            raise ValidationError(
                {
                    "position": (
                        "The question position cannot be greater "
                        "than the total number of questions."
                    ),
                },
            )

    def save(self, *args, **kwargs):
        self.full_clean()

        return super().save(
            *args,
            **kwargs,
        )

    def __str__(self):
        return (
            f"{self.attempt} - "
            f"Question {self.position}"
        )


class StudentAnswer(models.Model):
    attempt_question = models.OneToOneField(
        AttemptQuestion,
        on_delete=models.CASCADE,
        related_name="student_answer",
        
    )

    selected_option = models.ForeignKey(
        AnswerOption,
        on_delete=models.PROTECT,
        related_name="student_answers",
    )

    is_correct = models.BooleanField(
        default=False,
        editable=False,
    )

    answered_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "attempt_question__position",
        ]

    @property
    def attempt(self):
        return self.attempt_question.attempt

    @property
    def question(self):
        return self.attempt_question.question

    def clean(self):
        super().clean()

        if not (
            self.attempt_question_id
            and self.selected_option_id
        ):
            return

        if self.attempt_question.attempt.is_completed:
            raise ValidationError(
                "Answers from a completed attempt cannot be changed."
            )

        if (
            self.selected_option.question_id
            != self.attempt_question.question_id
        ):
            raise ValidationError(
                {
                    "selected_option": (
                        "The selected answer does not belong "
                        "to this question."
                    ),
                },
            )

    def save(self, *args, **kwargs):
        self.full_clean()

        self.is_correct = self.selected_option.is_correct

        return super().save(
            *args,
            **kwargs,
        )

    def delete(self, *args, **kwargs):
        if self.attempt_question.attempt.is_completed:
            raise ValidationError(
                "Answers from a completed attempt cannot be deleted."
            )

        return super().delete(
            *args,
            **kwargs,
        )

    def __str__(self):
        result = (
            "Correct"
            if self.is_correct
            else "Incorrect"
        )

        return (
            f"{self.attempt.enrollment.user.username} - "
            f"Question {self.attempt_question.position} - "
            f"{result}"
        )
