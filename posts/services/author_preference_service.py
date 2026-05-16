from posts.models import AuthorPreference
from django.core.exceptions import ValidationError


def set_author_preference(user, author, preference):
    """
    Set a user's preference for an author.
    
    Args:
        user: The user setting the preference
        author: The author the preference is for
        preference: One of 'normal', 'less', 'none'
    
    Returns:
        AuthorPreference instance
    
    Raises:
        ValidationError: If user tries to set preference for themselves
    """
    if author == user:
        raise ValidationError("You cannot set preferences for yourself.")
    
    preference_obj, created = AuthorPreference.objects.update_or_create(
        user=user,
        author=author,
        defaults={'preference': preference}
    )
    return preference_obj


def get_author_preference(user, author):
    """
    Get a user's preference for an author.
    
    Args:
        user: The user
        author: The author
    
    Returns:
        AuthorPreference instance or None
    """
    try:
        return AuthorPreference.objects.get(user=user, author=author)
    except AuthorPreference.DoesNotExist:
        return None


def get_authors_to_see_less(user):
    """
    Get authors that user wants to see less of.
    
    Args:
        user: The user
    
    Returns:
        QuerySet of User instances
    """
    from users.models import User
    author_ids = AuthorPreference.objects.filter(
        user=user,
        preference='less'
    ).values_list('author_id', flat=True)
    return User.objects.filter(id__in=author_ids)


def get_authors_to_hide(user):
    """
    Get authors that user wants to see none of.
    
    Args:
        user: The user
    
    Returns:
        QuerySet of User instances
    """
    from users.models import User
    author_ids = AuthorPreference.objects.filter(
        user=user,
        preference='none'
    ).values_list('author_id', flat=True)
    return User.objects.filter(id__in=author_ids)


def get_all_preferences(user):
    """
    Get all author preferences for a user.
    
    Args:
        user: The user
    
    Returns:
        QuerySet of AuthorPreference instances
    """
    return AuthorPreference.objects.filter(user=user).select_related('author')


def should_show_post(user, post_author):
    """
    Determine if a post from an author should be shown to a user.
    
    Args:
        user: The user viewing the feed
        post_author: The author of the post
    
    Returns:
        tuple: (should_show, preference_level)
        preference_level: 'normal', 'less', or 'none'
    """
    if not user.is_authenticated or user == post_author:
        return (True, 'normal')
    
    preference = get_author_preference(user, post_author)
    if preference:
        if preference.preference == 'none':
            return (False, 'none')
        elif preference.preference == 'less':
            return (True, 'less')
    
    return (True, 'normal')
