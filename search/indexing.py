"""Search vector indexing utilities for Users, Groups, and Posts."""
from django.contrib.postgres.search import SearchVector


def update_user_search_vector(user_id):
    """Update full-text search vector for a User with field weights."""
    from users.models import User
    return User.objects.filter(id=user_id).update(
        search_vector=(
            SearchVector('username', weight='A') +
            SearchVector('first_name', weight='A') +
            SearchVector('last_name', weight='A') +
            SearchVector('headline', weight='B') +
            SearchVector('bio', weight='C')
        )
    )


def update_group_search_vector(group_id):
    """Update full-text search vector for a Group with field weights."""
    from groups.models import Group
    return Group.objects.filter(id=group_id).update(
        search_vector=(
            SearchVector('name', weight='A') +
            SearchVector('description', weight='B')
        )
    )


def update_post_search_vector(post_id):
    """Update full-text search vector for a Post with field weights."""
    from posts.models import Post
    return Post.objects.filter(id=post_id).update(
        search_vector=(
            SearchVector('content', weight='B') +
            SearchVector('video_transcript', weight='C')
        )
    )
