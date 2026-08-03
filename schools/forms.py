from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import MultipleObjectsReturned
from django.db import transaction

from accounts.models import Enrollment
from courses.models import Course


User = get_user_model()


class SchoolEnrollmentForm(forms.Form):
    """
    Enroll an existing SkillStart Ireland student
    through the administrator's school.
    """

    student_email = forms.EmailField(
        label="Student email",
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "profile-form-control",
                "placeholder": "Enter the student's account email",
                "autocomplete": "email",
            }
        ),
        help_text=(
            "The student must already have an active "
            "SkillStart Ireland account."
        ),
    )

    course = forms.ModelChoiceField(
        label="Course",
        queryset=Course.objects.none(),
        required=True,
        empty_label="Select a course",
        widget=forms.Select(
            attrs={
                "class": "profile-form-control",
            }
        ),
    )

    def __init__(
        self,
        *args,
        school,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.school = school
        self.student = None

        self.fields["course"].queryset = (
            Course.objects
            .filter(is_published=True)
            .select_related("category")
            .order_by(
                "category__name",
                "title",
            )
        )

    def clean_student_email(self):
        """
        Find the student using an exact email address
        without exposing the platform's user list.
        """

        email = (
            self.cleaned_data["student_email"]
            .strip()
            .lower()
        )

        eligible_users = (
            User.objects
            .filter(
                email__iexact=email,
                is_active=True,
                is_staff=False,
                is_superuser=False,
            )
        )

        try:
            self.student = eligible_users.get()

        except User.DoesNotExist:
            raise forms.ValidationError(
                "No active student account was found "
                "with this email address."
            )

        except MultipleObjectsReturned:
            raise forms.ValidationError(
                "More than one account uses this email address. "
                "Please contact the SkillStart Ireland administrator."
            )

        return email

    def clean(self):
        cleaned_data = super().clean()

        course = cleaned_data.get("course")

        if not self.school.subscription_active:
            raise forms.ValidationError(
                "This school's subscription is currently inactive."
            )

        if not course or not self.student:
            return cleaned_data

        enrollment_exists = (
            Enrollment.objects
            .filter(
                user=self.student,
                course=course,
            )
            .exists()
        )

        if enrollment_exists:
            raise forms.ValidationError(
                "This student is already enrolled in the selected course."
            )

        student_already_belongs_to_school = (
            Enrollment.objects
            .filter(
                school=self.school,
                user=self.student,
            )
            .exists()
        )

        if (
            not student_already_belongs_to_school
            and not self.school.has_available_student_places
        ):
            raise forms.ValidationError(
                "This school has reached its current student limit."
            )

        return cleaned_data

    @transaction.atomic
    def save(self):
        """
        Create the enrollment and automatically associate
        it with the administrator's school.
        """

        if not self.is_valid():
            raise ValueError(
                "The enrollment form must be valid before saving."
            )

        return Enrollment.objects.create(
            user=self.student,
            course=self.cleaned_data["course"],
            school=self.school,
        )