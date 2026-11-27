from rest_framework.permissions import BasePermission
from .models import Profile
from django.contrib.auth.models import User

class IsEmployer(BasePermission):
    message = "Only users with an Employer role can perform this action."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.role == 'employer'
        )

class IsJobSeeker(BasePermission):
    message = "Only users with a Job Seeker role can perform this action."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.role == 'job_seeker'
        )