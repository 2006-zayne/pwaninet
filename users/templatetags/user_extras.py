from django import template
from django.contrib.auth import get_user_model

register = template.Library()
User = get_user_model()


@register.filter
def get_global_role_badge(user):
    """Returns badge info for global roles (President, Delegate, Verified)"""
    if not hasattr(user, 'global_role'):
        return None
    
    badges = {
        'PRESIDENT': {'class': 'bg-danger', 'icon': 'bi-crown-fill', 'label': 'President'},
        'DELEGATE': {'class': 'bg-warning', 'icon': 'bi-star-fill', 'label': 'Delegate'},
        'VERIFIED': {'class': 'bg-primary', 'icon': 'bi-check-circle-fill', 'label': 'Verified'},
    }
    
    return badges.get(user.global_role)


@register.filter
def get_group_role_badge(user, group):
    """Returns badge info for group-specific roles (Admin, Moderator, Delegate)"""
    if not group or not hasattr(user, 'group_memberships'):
        return None
    
    try:
        membership = user.group_memberships.get(group=group, status='APPROVED')
        badges = {
            'ADMIN': {'class': 'bg-danger', 'icon': 'bi-shield-fill-check', 'label': 'Admin'},
            'MODERATOR': {'class': 'bg-info', 'icon': 'bi-shield-fill', 'label': 'Moderator'},
            'DELEGATE': {'class': 'bg-warning', 'icon': 'bi-star-fill', 'label': 'Delegate'},
        }
        return badges.get(membership.role)
    except Exception:
        return None


@register.filter
def has_authority_badge(user, group=None):
    """Check if user has any authority badge (global or group-specific)"""
    if hasattr(user, 'global_role') and user.global_role in ['PRESIDENT', 'DELEGATE', 'VERIFIED']:
        return True
    
    if group and hasattr(user, 'group_memberships'):
        try:
            membership = user.group_memberships.get(group=group, status='APPROVED')
            return membership.role in ['ADMIN', 'MODERATOR', 'DELEGATE']
        except Exception:
            pass
    
    return False


@register.filter
def is_following(user, current_user):
    """Check if current_user is following user"""
    if not current_user.is_authenticated:
        return False
    from users.models import Follow
    return Follow.objects.filter(follower=current_user, followed=user).exists()


@register.filter
def can_pinch(user, current_user):
    """Check if current_user can pinch user"""
    if not current_user.is_authenticated:
        return False
    from users.models import Pinch
    can_pinch, _ = Pinch.can_pinch(current_user, user)
    return can_pinch
