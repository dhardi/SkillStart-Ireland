from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import StudentProfile


User = get_user_model()


@receiver(post_save, sender=User)
def create_student_profile(sender, instance, created, **kwargs):
    """
    Automatically create a StudentProfile whenever
    a new user account is created.
    """

    if created:
        StudentProfile.objects.get_or_create(
            user=instance,
        )