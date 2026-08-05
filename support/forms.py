from django import forms
from django.core.validators import FileExtensionValidator
from django.db import transaction
from django.contrib.auth import get_user_model

from accounts.models import Enrollment
from schools.models import School

from .models import (
    Ticket,
    TicketAttachment,
    TicketReply,
    validate_attachment_size,
)


ALLOWED_ATTACHMENT_EXTENSIONS = [
    "pdf",
    "png",
    "jpg",
    "jpeg",
    "webp",
    "doc",
    "docx",
    "txt",
]


class TicketCreateForm(forms.ModelForm):
    """
    Create a support ticket through the student
    area or school portal.
    """

    school = forms.ModelChoiceField(
        label="Related school",
        queryset=School.objects.none(),
        required=False,
        empty_label="Platform support — no school",
        widget=forms.Select(
            attrs={
                "class": "profile-form-control",
            }
        ),
        help_text=(
            "Select a school only when the request "
            "is related to that school."
        ),
    )

    attachment = forms.FileField(
        label="Attachment",
        required=False,
        validators=[
            FileExtensionValidator(
                allowed_extensions=(
                    ALLOWED_ATTACHMENT_EXTENSIONS
                )
            ),
            validate_attachment_size,
        ],
        widget=forms.ClearableFileInput(
            attrs={
                "class": "profile-form-control",
                "accept": (
                    ".pdf,.png,.jpg,.jpeg,.webp,"
                    ".doc,.docx,.txt"
                ),
            }
        ),
        help_text=(
            "Optional. PDF, image, Word document or "
            "text file. Maximum size: 10 MB."
        ),
    )

    class Meta:
        model = Ticket

        fields = (
            "subject",
            "category",
            "priority",
            "school",
            "description",
        )

        widgets = {
            "subject": forms.TextInput(
                attrs={
                    "class": "profile-form-control",
                    "placeholder": (
                        "Briefly describe the problem"
                    ),
                    "autocomplete": "off",
                }
            ),
            "category": forms.Select(
                attrs={
                    "class": "profile-form-control",
                }
            ),
            "priority": forms.Select(
                attrs={
                    "class": "profile-form-control",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "profile-form-control",
                    "rows": 8,
                    "placeholder": (
                        "Explain what happened, what you "
                        "expected and any error message shown."
                    ),
                }
            ),
        }

    def __init__(
        self,
        *args,
        user,
        portal_school=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.user = user
        self.portal_school = portal_school

        if portal_school is not None:
            # School tickets are automatically linked
            # to the school currently using the portal.
            self.fields.pop(
                "school",
                None,
            )

        else:
            school_ids = (
                Enrollment.objects
                .filter(
                    user=user,
                    school__isnull=False,
                    school__is_active=True,
                )
                .values_list(
                    "school_id",
                    flat=True,
                )
                .distinct()
            )

            self.fields["school"].queryset = (
                School.objects
                .filter(
                    pk__in=school_ids,
                    is_active=True,
                )
                .order_by("name")
            )

    def clean_school(self):
        """
        Prevent a student from associating the ticket
        with a school they do not belong to.
        """

        selected_school = self.cleaned_data.get(
            "school"
        )

        if selected_school is None:
            return None

        allowed_school = (
            self.fields["school"]
            .queryset
            .filter(pk=selected_school.pk)
            .exists()
        )

        if not allowed_school:
            raise forms.ValidationError(
                "You cannot create a ticket for this school."
            )

        return selected_school

    @transaction.atomic
    def save(self):
        """
        Save the ticket and optional first attachment
        inside one transaction.
        """

        ticket = super().save(
            commit=False
        )

        ticket.author = self.user
        ticket.status = "new"

        if self.portal_school is not None:
            ticket.school = self.portal_school
        else:
            ticket.school = self.cleaned_data.get(
                "school"
            )

        ticket.save()

        attachment = self.cleaned_data.get(
            "attachment"
        )

        if attachment:
            TicketAttachment.objects.create(
                ticket=ticket,
                uploaded_by=self.user,
                file=attachment,
                original_name=attachment.name,
            )

        return ticket


class TicketReplyForm(forms.Form):
    """
    Add a visible reply and optional attachment
    to an existing support ticket.
    """

    message = forms.CharField(
        label="Your reply",
        required=True,
        widget=forms.Textarea(
            attrs={
                "class": "profile-form-control",
                "rows": 6,
                "placeholder": (
                    "Write your reply or provide "
                    "additional information."
                ),
            }
        ),
    )

    attachment = forms.FileField(
        label="Attachment",
        required=False,
        validators=[
            FileExtensionValidator(
                allowed_extensions=(
                    ALLOWED_ATTACHMENT_EXTENSIONS
                )
            ),
            validate_attachment_size,
        ],
        widget=forms.ClearableFileInput(
            attrs={
                "class": "profile-form-control",
                "accept": (
                    ".pdf,.png,.jpg,.jpeg,.webp,"
                    ".doc,.docx,.txt"
                ),
            }
        ),
        help_text=(
            "Optional. Maximum file size: 10 MB."
        ),
    )

    def clean_message(self):
        message = self.cleaned_data[
            "message"
        ].strip()

        if not message:
            raise forms.ValidationError(
                "Please enter a reply."
            )

        return message

    @transaction.atomic
    def save(
        self,
        *,
        ticket,
        author,
    ):
        reply = TicketReply.objects.create(
            ticket=ticket,
            author=author,
            message=self.cleaned_data["message"],
            is_internal_note=False,
        )

        attachment = self.cleaned_data.get(
            "attachment"
        )

        if attachment:
            TicketAttachment.objects.create(
                ticket=ticket,
                reply=reply,
                uploaded_by=author,
                file=attachment,
                original_name=attachment.name,
            )

        return reply


class StaffTicketUpdateForm(forms.ModelForm):
    """
    Allow platform staff to manage ticket status,
    priority and assignment.
    """

    class Meta:
        model = Ticket

        fields = (
            "status",
            "priority",
            "assigned_to",
        )

        widgets = {
            "status": forms.Select(
                attrs={
                    "class": "management-form-control",
                }
            ),
            "priority": forms.Select(
                attrs={
                    "class": "management-form-control",
                }
            ),
            "assigned_to": forms.Select(
                attrs={
                    "class": "management-form-control",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        User = get_user_model()

        self.fields["assigned_to"].queryset = (
            User.objects
            .filter(
                is_staff=True,
                is_active=True,
            )
            .order_by(
                "first_name",
                "last_name",
                "username",
            )
        )

        self.fields["assigned_to"].required = False
        self.fields["assigned_to"].empty_label = (
            "Not assigned"
        )

    def save(self, commit=True):
        """
        Maintain resolved and closed timestamps
        whenever the ticket status changes.
        """

        ticket = super().save(commit=False)

        previous_status = None

        if ticket.pk:
            previous_status = (
                Ticket.objects
                .filter(pk=ticket.pk)
                .values_list(
                    "status",
                    flat=True,
                )
                .first()
            )

        from django.utils import timezone

        current_time = timezone.now()

        if ticket.status == "resolved":
            if previous_status != "resolved":
                ticket.resolved_at = current_time

            ticket.closed_at = None

        elif ticket.status == "closed":
            if previous_status != "closed":
                ticket.closed_at = current_time

            if ticket.resolved_at is None:
                ticket.resolved_at = current_time

        else:
            ticket.resolved_at = None
            ticket.closed_at = None

        if commit:
            ticket.save()

        return ticket


class StaffTicketReplyForm(forms.Form):
    """
    Allow platform staff to add a public reply
    or an internal administrative note.
    """

    message = forms.CharField(
        label="Message",
        required=True,
        widget=forms.Textarea(
            attrs={
                "class": "management-form-control",
                "rows": 7,
                "placeholder": (
                    "Write a response or internal note..."
                ),
            }
        ),
    )

    is_internal_note = forms.BooleanField(
        label="Internal note",
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "management-form-check-input",
            }
        ),
        help_text=(
            "Internal notes are visible only to "
            "SkillStart Ireland administrators."
        ),
    )

    attachment = forms.FileField(
        label="Attachment",
        required=False,
        validators=[
            FileExtensionValidator(
                allowed_extensions=(
                    ALLOWED_ATTACHMENT_EXTENSIONS
                )
            ),
            validate_attachment_size,
        ],
        widget=forms.ClearableFileInput(
            attrs={
                "class": "management-form-control",
                "accept": (
                    ".pdf,.png,.jpg,.jpeg,.webp,"
                    ".doc,.docx,.txt"
                ),
            }
        ),
        help_text=(
            "Optional. Maximum file size: 10 MB."
        ),
    )

    def clean_message(self):
        message = self.cleaned_data[
            "message"
        ].strip()

        if not message:
            raise forms.ValidationError(
                "Please enter a message."
            )

        return message

    @transaction.atomic
    def save(
        self,
        *,
        ticket,
        author,
    ):
        is_internal_note = self.cleaned_data.get(
            "is_internal_note",
            False,
        )

        reply = TicketReply.objects.create(
            ticket=ticket,
            author=author,
            message=self.cleaned_data["message"],
            is_internal_note=is_internal_note,
        )

        attachment = self.cleaned_data.get(
            "attachment"
        )

        if attachment:
            TicketAttachment.objects.create(
                ticket=ticket,
                reply=reply,
                uploaded_by=author,
                file=attachment,
                original_name=attachment.name,
            )

        if not is_internal_note:
            ticket.status = "waiting_user"

            if ticket.assigned_to_id is None:
                ticket.assigned_to = author

            ticket.resolved_at = None
            ticket.closed_at = None

            ticket.save(
                update_fields=[
                    "status",
                    "assigned_to",
                    "resolved_at",
                    "closed_at",
                    "updated_at",
                ]
            )

        return reply