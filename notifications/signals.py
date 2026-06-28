from django.db.models.signals import post_save
from django.dispatch import receiver
from posts.models import Like, Comment, CommentLike
from users.models import Follow, Pinch
from groups.models import Group
from notifications.services.notification_service import create_notification
from notifications.models import Notifications


@receiver(post_save, sender=Like)
def create_like_notification(sender, instance, created, **kwargs):
    if created:
        post = instance.post
        liker = instance.user
        post_author = post.author
        
        if liker != post_author:
            create_notification(
                recipient=post_author,
                sender=liker,
                notification_type=Notifications.LIKE,
                msg=f'{liker.username} liked your post',
                post=post
            )


@receiver(post_save, sender=Comment)
def create_comment_notification(sender, instance, created, **kwargs):
    if created:
        post = instance.post
        commenter = instance.author
        post_author = post.author
        
        if commenter != post_author:
            create_notification(
                recipient=post_author,
                sender=commenter,
                notification_type=Notifications.ALERTE,
                msg=f'{commenter.username} commented on your post',
                post=post
            )


@receiver(post_save, sender=CommentLike)
def create_comment_like_notification(sender, instance, created, **kwargs):
    if created:
        comment = instance.comment
        liker = instance.user
        comment_author = comment.author
        
        if liker != comment_author:
            create_notification(
                recipient=comment_author,
                sender=liker,
                notification_type=Notifications.ALERTE,
                msg=f'{liker.username} liked your comment',
                post=comment.post
            )


@receiver(post_save, sender=Follow)
def create_follow_notification(sender, instance, created, **kwargs):
    if created:
        follower = instance.follower
        followed = instance.followed
        
        create_notification(
                recipient=followed,
                sender=follower,
                notification_type=Notifications.FOLLOW,
                msg=f'{follower.username} started following you'
            )


@receiver(post_save, sender=Pinch)
def create_pinch_notification(sender, instance, created, **kwargs):
    if created:
        pinch_user = instance.pinch_user
        pinched_user = instance.pinched_user
        
        create_notification(
            recipient=pinched_user,
            sender=pinch_user,
            notification_type=Notifications.PINCH,
            msg=f'{pinch_user.username} pinched your profile'
        )
