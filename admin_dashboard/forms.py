from django import forms
from django.contrib.auth import get_user_model

from accounts.models import Enrollment
from courses.models import Course


User = get_user_model()


class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment

        fields = (
            "user",
            "course",
        )

        labels = {
            "user": "Student",
            "course": "Course",
        }

        widgets = {
            "user": forms.Select(
                attrs={
                    "class": "management-form-control",
                },
            ),
            "course": forms.Select(
                attrs={
                    "class": "management-form-control",
                },
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["user"].queryset = (
            User.objects
            .filter(
                is_staff=False,
                is_active=True,
            )
            .order_by(
                "first_name",
                "last_name",
                "username",
            )
        )

        self.fields["course"].queryset = (
            Course.objects
            .filter(
                is_published=True,
            )
            .select_related(
                "category",
            )
            .order_by(
                "title",
            )
        )

        self.fields["user"].empty_label = (
            "Select a student"
        )

        self.fields["course"].empty_label = (
            "Select a course"
        )

    def clean(self):
        cleaned_data = super().clean()

        user = cleaned_data.get("user")
        course = cleaned_data.get("course")

        if (
            user
            and course
            and Enrollment.objects.filter(
                user=user,
                course=course,
            ).exists()
        ):
            raise forms.ValidationError(
                (
                    "This student is already enrolled "
                    "in the selected course."
                )
            )

        return cleaned_data