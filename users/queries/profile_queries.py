from django.db.models import Count
from users.models import Follow
from posts.models import Post

def get_is_following(current_user, profile_user):
    return Follow.objects.filter(follower=current_user, followed=profile_user).exists()

def get_total_likes_for_user(profile_user):
    result = Post.objects.filter(author=profile_user).aggregate(total=Count('likes'))
    return result['total'] or 0

def get_user_posts(profile_user):
    return profile_user.posts.all().order_by('-created_at')

def get_following_count(profile_user):
    return Follow.objects.filter(follower=profile_user).count()

def get_followers_count(profile_user):
    return Follow.objects.filter(followed=profile_user).count()
