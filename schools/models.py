from django.conf import settings
from django.db import models


class School(models.Model):
    """
    Represents a school or training organisation
    using the SkillStart Ireland platform.
    """

    PLAN_CHOICES = [
        ("pilot", "Pilot"),
        ("starter", "Starter"),
        ("growth", "Growth"),
        ("custom", "Custom"),
    ]

    name = models.CharField(
        max_length=150,
        unique=True,
    )

    slug = models.SlugField(
        max_length=170,
        unique=True,
    )

    logo = models.ImageField(
        upload_to="schools/logos/",
        blank=True,
        null=True,
    )

    contact_email = models.EmailField(
        blank=True,
    )

    phone_number = models.CharField(
        max_length=30,
        blank=True,
    )

    plan = models.CharField(
        max_length=30,
        choices=PLAN_CHOICES,
        default="pilot",
    )

    student_limit = models.PositiveIntegerField(
        default=50,
    )

    subscription_active = models.BooleanField(
        default=True,
    )

    subscription_end_date = models.DateField(
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "name",
        ]

    @property
    def active_student_count(self):
        """
        Return the number of distinct students currently
        enrolled through this school.
        """

        return (
            self.enrollments
            .values("user")
            .distinct()
            .count()
        )

    @property
    def has_available_student_places(self):
        """
        Return True when the school can register
        additional students.
        """

        return (
            self.active_student_count
            < self.student_limit
        )

    def __str__(self):
        return self.name


class SchoolAdministrator(models.Model):
    """
    Connects a user account to the school
    that the user is authorised to manage.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="school_administrator",
    )

    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="administrators",
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "school__name",
            "user__username",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "school",
                    "user",
                ],
                name="unique_school_administrator",
            ),
        ]

    @property
    def display_name(self):
        full_name = self.user.get_full_name().strip()

        if full_name:
            return full_name

        return self.user.username

    def __str__(self):
        return (
            f"{self.display_name} - "
            f"{self.school.name}"
        )