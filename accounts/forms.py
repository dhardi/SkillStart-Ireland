from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import StudentProfile


User = get_user_model()


class StudentRegistrationForm(UserCreationForm):
    """
    Form used by students to create a SkillStart Ireland account.
    """

    first_name = forms.CharField(
        label="First name",
        max_length=150,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "register-form-control",
                "placeholder": "Enter your first name",
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
                "class": "register-form-control",
                "placeholder": "Enter your last name",
                "autocomplete": "family-name",
            }
        ),
    )

    username = forms.CharField(
        label="Username",
        max_length=150,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "register-form-control",
                "placeholder": "Choose a username",
                "autocomplete": "username",
            }
        ),
    )

    email = forms.EmailField(
        label="Email address",
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "register-form-control",
                "placeholder": "Enter your email address",
                "autocomplete": "email",
            }
        ),
    )

    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "register-form-control",
                "placeholder": "Create a secure password",
                "autocomplete": "new-password",
            }
        ),
    )

    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "register-form-control",
                "placeholder": "Enter your password again",
                "autocomplete": "new-password",
            }
        ),
    )

    class Meta:
        model = User

        fields = (
            "first_name",
            "last_name",
            "username",
            "email",
            "password1",
            "password2",
        )

    def clean_email(self):
        """
        Prevent different accounts from using the same email address.
        """

        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email address already exists."
            )

        return email

    def save(self, commit=True):
        """
        Save normalized student information.
        """

        user = super().save(commit=False)

        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name = self.cleaned_data["last_name"].strip()
        user.email = self.cleaned_data["email"].strip().lower()

        if commit:
            user.save()

        return user


class UserProfileForm(forms.ModelForm):
    """
    Form used to update the personal information
    stored in Django's User model.
    """

    first_name = forms.CharField(
        label="First name",
        max_length=150,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "profile-form-control",
                "placeholder": "Enter your first name",
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
                "placeholder": "Enter your last name",
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
                "placeholder": "Enter your email address",
                "autocomplete": "email",
            }
        ),
    )

    class Meta:
        model = User

        fields = (
            "first_name",
            "last_name",
            "email",
        )

    def clean_email(self):
        """
        Prevent the student from using an email address
        that belongs to another account.
        """

        email = self.cleaned_data["email"].strip().lower()

        email_is_in_use = (
            User.objects
            .filter(email__iexact=email)
            .exclude(pk=self.instance.pk)
            .exists()
        )

        if email_is_in_use:
            raise forms.ValidationError(
                "An account with this email address already exists."
            )

        return email

    def save(self, commit=True):
        """
        Save normalized profile information.
        """

        user = super().save(commit=False)

        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name = self.cleaned_data["last_name"].strip()
        user.email = self.cleaned_data["email"].strip().lower()

        if commit:
            user.save()

        return user


class StudentProfileForm(forms.ModelForm):
    """
    Form used to update the additional information
    stored in StudentProfile.
    """

    class Meta:
        model = StudentProfile

        fields = (
            "profile_photo",
            "phone_number",
            "preferred_language",
        )

        labels = {
            "profile_photo": "Profile photo",
            "phone_number": "Phone number",
            "preferred_language": "Preferred language",
        }

        widgets = {
            "profile_photo": forms.ClearableFileInput(
                attrs={
                    "class": "profile-form-file",
                    "accept": "image/png,image/jpeg,image/webp",
                }
            ),
            "phone_number": forms.TextInput(
                attrs={
                    "class": "profile-form-control",
                    "placeholder": "Enter your phone number",
                    "autocomplete": "tel",
                }
            ),
            "preferred_language": forms.Select(
                attrs={
                    "class": "profile-form-control",
                }
            ),
        }

    def clean_phone_number(self):
        """
        Remove unnecessary spaces from the phone number.
        """

        phone_number = self.cleaned_data.get(
            "phone_number",
            "",
        )

        return phone_number.strip()