from django import template
from django.utils import timezone
from datetime import timedelta

register = template.Library()


@register.filter
def is_today(value):
    """Check if the given date is today."""
    if not value:
        return False
    if isinstance(value, str):
        value = timezone.parse_datetime(value)
    return value.date() == timezone.now().date()


@register.filter
def is_yesterday(value):
    """Check if the given date is yesterday."""
    if not value:
        return False
    if isinstance(value, str):
        value = timezone.parse_datetime(value)
    yesterday = timezone.now().date() - timedelta(days=1)
    return value.date() == yesterday


@register.filter
def get_first_other_member(conversation, user):
    """Get the first member other than the specified user."""
    for member in conversation.members.all():
        if member.user != user:
            return member
    return None
