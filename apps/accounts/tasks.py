import logging
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.template import TemplateDoesNotExist

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def send_activation_email(self, user_id, activation_url, email):
    try:
        email_html_message = render_to_string(
            'emails/activation_email.html',
            {'activation_url': activation_url, 'user_id': user_id}
        )
    except TemplateDoesNotExist as e:
        logger.error(f"Template error for user_id={user_id}, email={email}: {str(e)}")
        return False
    email_plain_message = strip_tags(email_html_message)
    from_email = f'"JobBoard Support Team" <{settings.EMAIL_HOST_USER}>'
    email = EmailMultiAlternatives(
        subject="Activate Your JobBoard Account",
        body=email_plain_message,
        from_email=from_email,
        to=[email],
    )
    email.attach_alternative(email_html_message, "text/html")
    try:
        email.send(fail_silently=False)
        logger.info(f"Activation email sent successfully to {email} for user_id={user_id}")
    except Exception as e:
        logger.error(f"Failed to send activation email to {email} for user_id={user_id}: {str(e)}")
        try:
            self.retry(countdown=60)  # Retry after 60 seconds
        except self.MaxRetriesExceededError:
            logger.critical(f"Max retries exceeded for sending activation email to {email} for user_id={user_id}")
            return False
        return False
    return True


@shared_task(bind=True, max_retries=3)
def send_password_reset_email(self, user_id, reset_url, email):
    try:
        # Render HTML email template
        email_html_message = render_to_string(
            'emails/password_reset_email.html',  # Updated to match folder naming style
            {
                'reset_url': reset_url,
                'expiry_hours': 1  # Matches token expiry
            }
        )
    except TemplateDoesNotExist as e:
        logger.error(f"Template error for password reset user_id={user_id}, email={email}: {str(e)}")
        return False

    # Create plain text version
    email_plain_message = strip_tags(email_html_message)
    from_email = f'"JobBoard Support Team" <{settings.EMAIL_HOST_USER}>'

    # Prepare email with both HTML & plain text
    email_msg = EmailMultiAlternatives(
        subject="Password Reset Request",
        body=email_plain_message,
        from_email=from_email,
        to=[email],
    )
    email_msg.attach_alternative(email_html_message, "text/html")

    try:
        email_msg.send(fail_silently=False)
        logger.info(f"Password reset email sent successfully to {email} for user_id={user_id}")
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email} for user_id={user_id}: {str(e)}")
        try:
            self.retry(countdown=60)  # Retry after 60 seconds
        except self.MaxRetriesExceededError:
            logger.critical(f"Max retries exceeded for sending password reset email to {email} for user_id={user_id}")
            return False
        return False

    return True

