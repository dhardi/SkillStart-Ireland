import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models


MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024


def validate_attachment_size(uploaded_file):
    """
    Limit support attachments to 10 MB.
    """

    if uploaded_file.size > MAX_ATTACHMENT_SIZE:
        raise ValidationError(
            "The attachment cannot be larger than 10 MB."
        )


def support_attachment_upload_path(instance, filename):
    """
    Store support attachments using a safe generated filename.
    """

    extension = Path(filename).suffix.lower()

    generated_filename = (
        f"{uuid.uuid4().hex}{extension}"
    )

    ticket_folder = (
        instance.ticket.ticket_number
        or "pending-ticket"
    )

    return (
        f"support/"
        f"{ticket_folder}/"
        f"{generated_filename}"
    )


class Ticket(models.Model):
    """
    A support request created by a student,
    school administrator or platform administrator.
    """

    CATEGORY_CHOICES = [
        ("technical", "Technical problem"),
        ("account", "Account and login"),
        ("course", "Course content"),
        ("assessment", "Assessment"),
        ("certificate", "Certificate"),
        ("enrollment", "Enrollment"),
        ("billing", "Billing and subscription"),
        ("school", "School management"),
        ("other", "Other"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("normal", "Normal"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    STATUS_CHOICES = [
        ("new", "New"),
        ("open", "Open"),
        ("waiting_user", "Waiting for user"),
        ("waiting_support", "Waiting for support"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    ]

    ticket_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        blank=True,
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="support_tickets",
    )

    school = models.ForeignKey(
        "schools.School",
        on_delete=models.PROTECT,
        related_name="support_tickets",
        blank=True,
        null=True,
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_support_tickets",
        blank=True,
        null=True,
        limit_choices_to={
            "is_staff": True,
        },
    )

    subject = models.CharField(
        max_length=180,
    )

    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default="technical",
    )

    description = models.TextField()

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="normal",
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="new",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    resolved_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    closed_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        ordering = [
            "-updated_at",
            "-created_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "status",
                    "-updated_at",
                ],
                name="support_status_updated_idx",
            ),
            models.Index(
                fields=[
                    "school",
                    "-created_at",
                ],
                name="support_school_created_idx",
            ),
            models.Index(
                fields=[
                    "author",
                    "-created_at",
                ],
                name="support_author_created_idx",
            ),
        ]

    @classmethod
    def generate_ticket_number(cls):
        """
        Generate a readable and unique ticket number.
        """

        while True:
            random_code = (
                uuid.uuid4()
                .hex[:8]
                .upper()
            )

            ticket_number = (
                f"SSI-{random_code}"
            )

            if not cls.objects.filter(
                ticket_number=ticket_number,
            ).exists():
                return ticket_number

    @property
    def is_finished(self):
        return self.status in {
            "resolved",
            "closed",
        }

    @property
    def author_display_name(self):
        full_name = (
            self.author
            .get_full_name()
            .strip()
        )

        return (
            full_name
            or self.author.username
        )

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            self.ticket_number = (
                self.generate_ticket_number()
            )

        super().save(
            *args,
            **kwargs,
        )

    def __str__(self):
        return (
            f"{self.ticket_number} - "
            f"{self.subject}"
        )


class TicketReply(models.Model):
    """
    A reply or update added to a support ticket.
    """

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="replies",
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="support_ticket_replies",
    )

    message = models.TextField()

    is_internal_note = models.BooleanField(
        default=False,
        help_text=(
            "Internal notes are visible only "
            "to platform administrators."
        ),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "created_at",
        ]

    @property
    def author_display_name(self):
        full_name = (
            self.author
            .get_full_name()
            .strip()
        )

        return (
            full_name
            or self.author.username
        )

    def __str__(self):
        return (
            f"Reply to {self.ticket.ticket_number} "
            f"by {self.author_display_name}"
        )


class TicketAttachment(models.Model):
    """
    A file attached to a ticket or ticket reply.
    """

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    reply = models.ForeignKey(
        TicketReply,
        on_delete=models.CASCADE,
        related_name="attachments",
        blank=True,
        null=True,
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="support_attachments",
    )

    file = models.FileField(
        upload_to=support_attachment_upload_path,
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "pdf",
                    "png",
                    "jpg",
                    "jpeg",
                    "webp",
                    "doc",
                    "docx",
                    "txt",
                ]
            ),
            validate_attachment_size,
        ],
    )

    original_name = models.CharField(
        max_length=255,
        blank=True,
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "uploaded_at",
        ]

    def clean(self):
        super().clean()

        if (
            self.reply_id
            and self.ticket_id
            and self.reply.ticket_id
            != self.ticket_id
        ):
            raise ValidationError(
                {
                    "reply": (
                        "The selected reply does not "
                        "belong to this ticket."
                    ),
                }
            )

    def save(self, *args, **kwargs):
        if (
            self.file
            and not self.original_name
        ):
            self.original_name = (
                Path(self.file.name).name
            )

        self.full_clean()

        super().save(
            *args,
            **kwargs,
        )

    def __str__(self):
        return (
            f"{self.original_name} - "
            f"{self.ticket.ticket_number}"
        )