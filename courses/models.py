from urllib.parse import parse_qs, urlparse

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Category(models.Model):
    name = models.CharField(
        max_length=100,
    )

    description = models.TextField(
        blank=True,
    )

    slug = models.SlugField(
        max_length=120,
        unique=True,
    )

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ("name",)

    def __str__(self):
        return self.name


class Course(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="courses",
    )

    title = models.CharField(
        max_length=150,
    )

    description = models.TextField()

    slug = models.SlugField(
        max_length=170,
        unique=True,
    )

    image = models.ImageField(
        upload_to="courses/",
        blank=True,
        null=True,
    )

    is_free = models.BooleanField(
        default=True,
    )

    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
    )

    currency = models.CharField(
        max_length=3,
        default="EUR",
    )

    is_published = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ("title",)

    def __str__(self):
        return self.title


class Lesson(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="lessons",
    )

    title = models.CharField(
        max_length=150,
    )

    content = models.TextField(
        blank=True,
    )

    image = models.ImageField(
        upload_to="lessons/images/",
        blank=True,
        null=True,
    )

    video_url = models.URLField(
        blank=True,
    )

    order = models.PositiveIntegerField(
        default=1,
    )

    is_published = models.BooleanField(
        default=False,
    )

    class Meta:
        ordering = ("order",)

    @property
    def youtube_video_id(self):
        if not self.video_url:
            return None

        parsed_url = urlparse(self.video_url)
        hostname = parsed_url.hostname or ""

        if hostname in {
            "youtu.be",
            "www.youtu.be",
        }:
            return (
                parsed_url.path
                .lstrip("/")
                .split("/")[0]
            )

        if hostname in {
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
        }:
            if parsed_url.path == "/watch":
                return parse_qs(
                    parsed_url.query,
                ).get(
                    "v",
                    [None],
                )[0]

            if parsed_url.path.startswith("/embed/"):
                return (
                    parsed_url.path
                    .split("/embed/")[1]
                    .split("/")[0]
                )

            if parsed_url.path.startswith("/shorts/"):
                return (
                    parsed_url.path
                    .split("/shorts/")[1]
                    .split("/")[0]
                )

        return None

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class CourseAssessment(models.Model):
    course = models.OneToOneField(
        Course,
        on_delete=models.CASCADE,
        related_name="assessment",
    )

    title = models.CharField(
        max_length=180,
        default="Final Assessment",
    )

    instructions = models.TextField(
        blank=True,
        default=(
            "Answer every question and select one answer "
            "for each question."
        ),
    )

    passing_score = models.PositiveSmallIntegerField(
        default=80,
        help_text=(
            "Minimum percentage required to pass."
        ),
    )

    questions_per_attempt = models.PositiveSmallIntegerField(
        default=20,
        help_text=(
            "Number of questions presented in each attempt."
        ),
    )

    maximum_attempts = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        help_text=(
            "Leave empty to allow unlimited attempts."
        ),
    )

    shuffle_questions = models.BooleanField(
        default=True,
    )

    shuffle_answers = models.BooleanField(
        default=True,
    )

    is_published = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Course assessment"
        verbose_name_plural = "Course assessments"
        ordering = ("course__title",)

    def clean(self):
        super().clean()

        if self.passing_score < 1 or self.passing_score > 100:
            raise ValidationError(
                {
                    "passing_score": (
                        "The passing score must be between "
                        "1 and 100."
                    ),
                },
            )

        if self.questions_per_attempt < 1:
            raise ValidationError(
                {
                    "questions_per_attempt": (
                        "The assessment must contain at "
                        "least one question."
                    ),
                },
            )

        if (
            self.maximum_attempts is not None
            and self.maximum_attempts < 1
        ):
            raise ValidationError(
                {
                    "maximum_attempts": (
                        "Maximum attempts must be at least "
                        "1 or left empty."
                    ),
                },
            )

    @property
    def required_correct_answers(self):
        return (
            self.questions_per_attempt
            * self.passing_score
            + 99
        ) // 100

    @property
    def published_question_count(self):
        return self.questions.filter(
            is_published=True,
        ).count()

    @property
    def is_ready(self):
        published_questions = self.questions.filter(
            is_published=True,
        ).prefetch_related(
            "answer_options",
        )

        if (
            published_questions.count()
            < self.questions_per_attempt
        ):
            return False

        return all(
            question.is_ready
            for question in published_questions
        )

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Question(models.Model):
    assessment = models.ForeignKey(
        CourseAssessment,
        on_delete=models.CASCADE,
        related_name="questions",
    )

    text = models.TextField()

    explanation = models.TextField(
        blank=True,
        help_text=(
            "Optional explanation shown after the attempt."
        ),
    )

    order = models.PositiveIntegerField(
        default=1,
    )

    is_published = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = (
            "order",
            "id",
        )

        constraints = [
            models.UniqueConstraint(
                fields=(
                    "assessment",
                    "order",
                ),
                name="unique_question_order_per_assessment",
            ),
        ]

    @property
    def correct_answer(self):
        return self.answer_options.filter(
            is_correct=True,
        ).first()

    @property
    def is_ready(self):
        options = self.answer_options.all()

        return (
            options.count() == 4
            and options.filter(
                is_correct=True,
            ).count() == 1
        )

    def __str__(self):
        return (
            f"{self.assessment.course.title} - "
            f"Question {self.order}"
        )


class AnswerOption(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="answer_options",
    )

    text = models.CharField(
        max_length=500,
    )

    is_correct = models.BooleanField(
        default=False,
    )

    order = models.PositiveSmallIntegerField(
        default=1,
    )

    class Meta:
        ordering = (
            "order",
            "id",
        )

        constraints = [
            models.UniqueConstraint(
                fields=(
                    "question",
                    "order",
                ),
                name="unique_answer_order_per_question",
            ),
            models.UniqueConstraint(
                fields=("question",),
                condition=Q(is_correct=True),
                name="one_correct_answer_per_question",
            ),
        ]

    def clean(self):
        super().clean()

        if self.order < 1 or self.order > 4:
            raise ValidationError(
                {
                    "order": (
                        "The answer position must be "
                        "between 1 and 4."
                    ),
                },
            )

        # When a new Question is created in Django Admin, its inline
        # answers are validated before the Question receives an ID.
        if not self.question_id:
            return

        existing_options = AnswerOption.objects.filter(
            question_id=self.question_id,
        )

        if self.pk:
            existing_options = existing_options.exclude(
                pk=self.pk,
            )

        if existing_options.count() >= 4:
            raise ValidationError(
                {
                    "question": (
                        "Each question can have exactly "
                        "four answer options."
                    ),
                },
            )

        if (
            self.is_correct
            and existing_options.filter(
                is_correct=True,
            ).exists()
        ):
            raise ValidationError(
                {
                    "is_correct": (
                        "Only one answer option can be "
                        "marked as correct."
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
        correct_label = (
            "Correct"
            if self.is_correct
            else "Incorrect"
        )

        return (
            f"Answer {self.order}: "
            f"{self.text} ({correct_label})"
        )
