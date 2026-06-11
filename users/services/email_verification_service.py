from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def send_verification_email(user):
    """
    Send email verification email to user.
    
    This is a non-blocking verification - users can still login without verification.
    Verification is primarily for future account recovery and trust features.
    """
    if user.email_verified:
        # Already verified, don't send another email
        return False
    
    # Generate verification token
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    # Build verification URL
    # In production, this should use the actual domain from settings
    verification_url = f"http://{settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost:8000'}/users/verify-email/{uid}/{token}/"
    
    # Render email content
    context = {
        'user': user,
        'verification_url': verification_url,
        'site_name': 'Pwaninet',
    }
    
    subject = 'Verify your email address on Pwaninet'
    html_message = render_to_string('users/emails/verification_email.html', context)
    plain_message = render_to_string('users/emails/verification_email.txt', context)
    
    # Send email
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        # Log error but don't fail registration
        print(f"Failed to send verification email: {e}")
        return False


def verify_email_token(user, token):
    """
    Verify email verification token.
    Returns True if token is valid, False otherwise.
    """
    if default_token_generator.check_token(user, token):
        user.email_verified = True
        user.save()
        return True
    return False
