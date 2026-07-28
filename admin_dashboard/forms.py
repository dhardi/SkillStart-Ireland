from django import forms
from django.contrib.auth import get_user_model

from accounts.models import Enrollment
from courses.models import Course, Lesson


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


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson

        fields = (
            "course",
            "title",
            "content",
            "image",
            "video_url",
            "order",
            "is_published",
        )

        labels = {
            "course": "Course",
            "title": "Lesson title",
            "content": "Lesson content",
            "image": "Lesson image",
            "video_url": "YouTube video URL",
            "order": "Lesson order",
            "is_published": "Publish lesson",
        }

        widgets = {
            "course": forms.Select(
                attrs={
                    "class": "management-form-control",
                },
            ),
            "title": forms.TextInput(
                attrs={
                    "class": "management-form-control",
                    "placeholder": "Enter the lesson title",
                },
            ),
            "content": forms.Textarea(
                attrs={
                    "class": "management-form-control",
                    "rows": 12,
                    "placeholder": "Enter the lesson content",
                },
            ),
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "management-form-control",
                    "accept": "image/*",
                },
            ),
            "video_url": forms.URLInput(
                attrs={
                    "class": "management-form-control",
                    "placeholder": (
                        "https://www.youtube.com/watch?v=..."
                    ),
                },
            ),
            "order": forms.NumberInput(
                attrs={
                    "class": "management-form-control",
                    "min": 1,
                },
            ),
            "is_published": forms.CheckboxInput(
                attrs={
                    "class": "management-form-check-input",
                },
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["course"].queryset = (
            Course.objects
            .select_related("category")
            .order_by(
                "category__name",
                "title",
            )
        )

        self.fields["course"].empty_label = (
            "Select a course"
        )

    def clean_order(self):
        order = self.cleaned_data.get("order")

        if order is not None and order < 1:
            raise forms.ValidationError(
                "Lesson order must be at least 1."
            )

        return order
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["course"].queryset = (
            Course.objects
            .select_related("category")
            .order_by(
                "category__name",
                "title",
            )
        )

        self.fields["course"].empty_label = (
            "Select a course"
        )

    def clean_order(self):
        order = self.cleaned_data.get("order")

        if order is not None and order < 1:
            raise forms.ValidationError(
                "Lesson order must be at least 1."
            )

        return order