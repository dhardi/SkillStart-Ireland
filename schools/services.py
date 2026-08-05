from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def send_student_invitation(
    *,
    request,
    student,
    school,
    course,
):
    """
    Send a secure invitation link that allows
    the new student to define their own password.
    """

    uid = urlsafe_base64_encode(
        force_bytes(student.pk)
    )

    token = default_token_generator.make_token(
        student
    )

    invitation_path = reverse(
        "accounts:password_reset_confirm",
        kwargs={
            "uidb64": uid,
            "token": token,
        },
    )

    invitation_url = request.build_absolute_uri(
        invitation_path
    )

    context = {
        "student": student,
        "school": school,
        "course": course,
        "invitation_url": invitation_url,
    }

    subject = render_to_string(
        "schools/emails/student_invitation_subject.txt",
        context,
    )

    subject = " ".join(
        subject.splitlines()
    ).strip()

    message = render_to_string(
        "schools/emails/student_invitation_email.txt",
        context,
    )

    return send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[student.email],
        fail_silently=False,
    )