import logging

from django.conf import settings
from django.core.mail import get_connection, send_mail

logger = logging.getLogger(__name__)


def send_application_status_email(application):
    """
    Sends an email to the applicant when their application status is updated.
    Catches delivery failures so status updates never fail due to mail issues.
    """
    applicant = getattr(application, "applicant", None)
    job = getattr(application, "job", None)
    if applicant is None or job is None:
        logger.warning(
            "Skipping status email for application id=%s due to missing applicant or job.",
            getattr(application, "pk", None),
        )
        return

    recipient_email = (getattr(applicant, "email", "") or "").strip()
    if not recipient_email:
        logger.info(
            "Skipping status email for application id=%s (applicant=%s has no email).",
            application.pk,
            applicant.username,
        )
        return

    status_display = application.get_status_display()
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@jobportal.local")

    subject = f"Application Update: {job.title} at {job.company} ({status_display})"
    message = (
        f"Hi {applicant.username},\n\n"
        f"Your application for the position of '{job.title}' at '{job.company}' "
        f"has been updated to: {status_display}.\n\n"
        f"Location: {job.location}\n"
        f"Current Status: {status_display}\n\n"
        f"Best regards,\n"
        f"Job Portal Team"
    )

    try:
        connection = get_connection(mailer="default")
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[recipient_email],
            connection=connection,
            fail_silently=False,
        )
    except Exception:
        logger.exception(
            "Failed to send application status email for application id=%s to %s",
            application.pk,
            recipient_email,
        )