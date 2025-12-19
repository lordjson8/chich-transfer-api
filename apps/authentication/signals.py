"""
Authentication signals
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """Actions after user is saved"""
    if created:
        # User just registered
        pass
