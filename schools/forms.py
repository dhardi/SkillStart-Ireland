from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import MultipleObjectsReturned
from django.db import transaction
from django.utils.text import slugify

from accounts.models import (
    Enrollment,
    StudentProfile,
)
from courses.models import Course

from .models import SchoolStudent


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

        membership = (
            SchoolStudent.objects
            .filter(
                school=self.school,
                user=self.student,
            )
            .first()
        )

        if membership and not membership.is_active:
            raise forms.ValidationError(
                "This student is currently inactive for this school. "
                "Reactivate the student before adding another course."
            )

        if (
            membership is None
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

        SchoolStudent.objects.get_or_create(
            school=self.school,
            user=self.student,
            defaults={
                "is_active": True,
            },
        )

        return Enrollment.objects.create(
            user=self.student,
            course=self.cleaned_data["course"],
            school=self.school,
        )


class SchoolStudentCreateForm(forms.Form):
    """
    Create a new SkillStart Ireland student account,
    student profile and initial school enrollment.
    """

    first_name = forms.CharField(
        label="First name",
        max_length=150,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "profile-form-control",
                "placeholder": "Enter the student's first name",
                "autocomplete": "given-name",
            }
        ),
    )

    last_name = forms.CharField(
        label="Last name",
        max_length=150,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "profile-form-control",
                "placeholder": "Enter the student's last name",
                "autocomplete": "family-name",
            }
        ),
    )

    email = forms.EmailField(
        label="Email address",
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "profile-form-control",
                "placeholder": "Enter the student's email",
                "autocomplete": "email",
            }
        ),
        help_text=(
            "A secure invitation to create a password "
            "will be sent to this email address."
        ),
    )

    phone_number = forms.CharField(
        label="Phone number",
        max_length=30,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "profile-form-control",
                "placeholder": "Optional phone number",
                "autocomplete": "tel",
            }
        ),
    )

    preferred_language = forms.ChoiceField(
        label="Preferred language",
        choices=StudentProfile.LANGUAGE_CHOICES,
        initial="en",
        required=True,
        widget=forms.Select(
            attrs={
                "class": "profile-form-control",
            }
        ),
    )

    course = forms.ModelChoiceField(
        label="Initial course",
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

        self.fields["course"].queryset = (
            Course.objects
            .filter(is_published=True)
            .select_related("category")
            .order_by(
                "category__name",
                "title",
            )
        )

    def clean_email(self):
        """
        Prevent the creation of another account
        using an email already registered.
        """

        email = (
            self.cleaned_data["email"]
            .strip()
            .lower()
        )

        if User.objects.filter(
            email__iexact=email,
        ).exists():
            raise forms.ValidationError(
                "An account already exists with this email address. "
                "Use Enroll existing student to connect that account "
                "to a course."
            )

        return email

    def clean_phone_number(self):
        """
        Remove unnecessary spaces from the phone number.
        """

        phone_number = self.cleaned_data.get(
            "phone_number",
            "",
        )

        return phone_number.strip()

    def clean(self):
        """
        Check the school subscription and student limit
        before creating the new account.
        """

        cleaned_data = super().clean()

        if not self.school.subscription_active:
            raise forms.ValidationError(
                "This school's subscription is currently inactive."
            )

        if not self.school.has_available_student_places:
            raise forms.ValidationError(
                "This school has reached its current student limit."
            )

        return cleaned_data

    def generate_unique_username(self):
        """
        Generate a readable username from the student's name.

        When the username already exists, add a sequential
        number to the end.
        """

        first_name = self.cleaned_data[
            "first_name"
        ].strip()

        last_name = self.cleaned_data[
            "last_name"
        ].strip()

        email = self.cleaned_data["email"]

        base_username = slugify(
            f"{first_name}-{last_name}"
        )

        if not base_username:
            base_username = slugify(
                email.split("@")[0]
            )

        if not base_username:
            base_username = "student"

        base_username = base_username[:140]

        username = base_username
        number = 2

        while User.objects.filter(
            username__iexact=username,
        ).exists():
            suffix = f"-{number}"

            available_length = (
                150 - len(suffix)
            )

            username = (
                f"{base_username[:available_length]}"
                f"{suffix}"
            )

            number += 1

        return username

    @transaction.atomic
    def save(self):
        """
        Create the user, student profile and initial
        enrollment inside one database transaction.
        """

        if not self.is_valid():
            raise ValueError(
                "The student form must be valid before saving."
            )

        username = self.generate_unique_username()

        student = User(
            username=username,
            first_name=(
                self.cleaned_data["first_name"]
                .strip()
            ),
            last_name=(
                self.cleaned_data["last_name"]
                .strip()
            ),
            email=self.cleaned_data["email"],
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )

        # A school administrator must never create or know
        # the student's password. The student will define
        # the password using the secure invitation link.
        student.set_unusable_password()
        student.save()

        StudentProfile.objects.update_or_create(
            user=student,
            defaults={
                "phone_number": self.cleaned_data[
                    "phone_number"
                ],
                "preferred_language": self.cleaned_data[
                    "preferred_language"
                ],
            },
        )

        SchoolStudent.objects.create(
            school=self.school,
            user=student,
            is_active=True,
        )

        enrollment = Enrollment.objects.create(
            user=student,
            course=self.cleaned_data["course"],
            school=self.school,
        )

        return student, enrollment


class SchoolStudentUpdateForm(forms.Form):
    """
    Update the personal information of a student
    connected to a school.
    """

    first_name = forms.CharField(
        label="First name",
        max_length=150,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "profile-form-control",
                "autocomplete": "given-name",
            }
        ),
    )

    last_name = forms.CharField(
        label="Last name",
        max_length=150,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "profile-form-control",
                "autocomplete": "family-name",
            }
        ),
    )

    email = forms.EmailField(
        label="Email address",
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "profile-form-control",
                "autocomplete": "email",
            }
        ),
    )

    phone_number = forms.CharField(
        label="Phone number",
        max_length=30,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "profile-form-control",
                "autocomplete": "tel",
            }
        ),
    )

    preferred_language = forms.ChoiceField(
        label="Preferred language",
        choices=StudentProfile.LANGUAGE_CHOICES,
        required=True,
        widget=forms.Select(
            attrs={
                "class": "profile-form-control",
            }
        ),
    )

    def __init__(
        self,
        *args,
        student,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.student = student

        profile, _ = StudentProfile.objects.get_or_create(
            user=student
        )

        if not self.is_bound:
            self.initial.update(
                {
                    "first_name": student.first_name,
                    "last_name": student.last_name,
                    "email": student.email,
                    "phone_number": profile.phone_number,
                    "preferred_language": (
                        profile.preferred_language
                    ),
                }
            )

    def clean_email(self):
        email = (
            self.cleaned_data["email"]
            .strip()
            .lower()
        )

        email_exists = (
            User.objects
            .filter(email__iexact=email)
            .exclude(pk=self.student.pk)
            .exists()
        )

        if email_exists:
            raise forms.ValidationError(
                "An account with this email address already exists."
            )

        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get(
            "phone_number",
            "",
        )

        return phone_number.strip()

    @transaction.atomic
    def save(self):
        if not self.is_valid():
            raise ValueError(
                "The student update form must be valid before saving."
            )

        student = self.student

        student.first_name = (
            self.cleaned_data["first_name"].strip()
        )

        student.last_name = (
            self.cleaned_data["last_name"].strip()
        )

        student.email = self.cleaned_data["email"]

        student.save(
            update_fields=[
                "first_name",
                "last_name",
                "email",
            ]
        )

        StudentProfile.objects.update_or_create(
            user=student,
            defaults={
                "phone_number": (
                    self.cleaned_data["phone_number"]
                ),
                "preferred_language": (
                    self.cleaned_data[
                        "preferred_language"
                    ]
                ),
            },
        )

        return student
