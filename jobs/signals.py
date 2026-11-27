from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Profile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically creates a Profile when a User is created.
    Assigns 'admin' if superuser, otherwise defaults to 'job_seeker'.
    """
    if created:
        role = 'admin' if instance.is_superuser else 'job_seeker'
        Profile.objects.create(user=instance, role=role)