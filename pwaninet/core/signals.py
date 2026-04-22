# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Groups ,Notifications , Like , Follow
from .services.notification_service import invalidate_unread_count_cache

@receiver(post_save, sender=User)
def auto_join_course_group(sender, instance, created, **kwargs):
    """
    Scans registration data and assigns user to their official 
    Academic Unit Group automatically.
    """
    # Only execute for NEW users who have completed their profile intel
    if created and instance.course and instance.year:
        
        # Standardize the naming convention for official groups
        # e.g., "Computer Science - Year 1"
        target_group_name = f"{instance.course.name} - Year {instance.year.level}"
        
        # Logic: Search for the group. If it doesn't exist, create it.
        # 'get_or_create' returns a tuple: (object, created_bool)
        group, created_group = Groups.objects.get_or_create(
            name=target_group_name,
            defaults={
                'description': f"Official academic hub for {target_group_name} operatives.",
                'is_official': True # Mark as system-generated, not user-made
            }
        )
        
        # Deploy the user into the group roster
        group.members.add(instance)


@receiver(post_save, sender=Like)
def notify_post_owner_on_like(sender, instance, created, **kwargs):
    """Protocol: Alert operative when their intel is endorsed."""
    if created:
        # Don't notify if the user likes their own post
        if instance.user != instance.post.author:
            Notifications.objects.create(
                recipient=instance.post.author,
                sender=instance.user,
                notification_type='LIKE',
                post=instance.post,
                msg="liked your field intel."
            )
            invalidate_unread_count_cache(instance.post.author_id)

@receiver(post_save, sender=Follow)
def notify_user_on_follow(sender, instance, created, **kwargs):
    """Protocol: Alert operative when they gain a new squad member."""
    if created:
        Notifications.objects.create(
            recipient=instance.followed,
            sender=instance.follower,
            notification_type='FOLLOW',
            msg="started following your tactical updates."
        )
        invalidate_unread_count_cache(instance.followed_id)