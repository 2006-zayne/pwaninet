# Source Generated with Decompyle++
# File: profile_service.cpython-312.pyc (Python 3.12)

from core.queries.profile_queries import get_followers_count, get_following_count, get_is_following, get_total_likes_for_user, get_user_posts

def build_profile_context(current_user, profile_user):
    return {
        'profile_user': profile_user,
        'following_count': get_following_count(profile_user),
        'followers_count': get_followers_count(profile_user),
        'total_likes': get_total_likes_for_user(profile_user),
        'posts': get_user_posts(profile_user),
        'is_following': get_is_following(current_user, profile_user) }

