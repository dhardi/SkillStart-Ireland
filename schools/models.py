from django.conf import settings
from django.db import models
from django.utils import timezone


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
        Return the number of active students
        currently connected to this school.
        """

        return self.student_memberships.filter(
            is_active=True,
        ).count()

    @property
    def has_available_student_places(self):
        """
        Return True when the school can register
        additional active students.
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


class SchoolStudent(models.Model):
    """
    Represents the relationship between a student
    and a school.

    Deactivating this relationship must not deactivate
    the student's global SkillStart Ireland account.
    """

    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="student_memberships",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="school_memberships",
    )

    is_active = models.BooleanField(
        default=True,
    )

    deactivated_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "user__first_name",
            "user__last_name",
            "user__username",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "school",
                    "user",
                ],
                name="unique_school_student",
            ),
        ]

    @property
    def display_name(self):
        full_name = self.user.get_full_name().strip()

        if full_name:
            return full_name

        return self.user.username

    def deactivate(self):
        """
        Deactivate the student's membership
        with this school only.
        """

        if not self.is_active:
            return

        self.is_active = False
        self.deactivated_at = timezone.now()

        self.save(
            update_fields=[
                "is_active",
                "deactivated_at",
                "updated_at",
            ]
        )

    def reactivate(self):
        """
        Reactivate the student's membership
        with this school.
        """

        if self.is_active:
            return

        self.is_active = True
        self.deactivated_at = None

        self.save(
            update_fields=[
                "is_active",
                "deactivated_at",
                "updated_at",
            ]
        )

    def __str__(self):
        return (
            f"{self.display_name} - "
            f"{self.school.name}"
        )