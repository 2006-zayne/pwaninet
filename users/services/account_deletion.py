import uuid
import logging

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import router, transaction
from django.db.models import FileField
from django.db.models.deletion import Collector

logger = logging.getLogger(__name__)


def _collect_files(collector):
    files = []
    collected_ids = {}
    for model, instances in collector.data.items():
        ids = {instance.pk for instance in instances}
        collected_ids[model] = ids
        for instance in instances:
            for field in model._meta.concrete_fields:
                if not isinstance(field, FileField):
                    continue
                value = getattr(instance, field.name, None)
                if value and value.name:
                    files.append((field.storage, value.name))
    return files, collected_ids


def _delete_unreferenced_files(files, collected_ids):
    seen = set()
    for storage, name in files:
        key = (id(storage), name)
        if key in seen:
            continue
        seen.add(key)

        referenced = False
        for model in apps.get_models():
            excluded_ids = collected_ids.get(model, set())
            for field in model._meta.concrete_fields:
                if not isinstance(field, FileField):
                    continue
                query = model._default_manager.filter(**{field.name: name})
                if excluded_ids:
                    query = query.exclude(pk__in=excluded_ids)
                if query.exists():
                    referenced = True
                    break
            if referenced:
                break
        if not referenced:
            try:
                storage.delete(name)
            except Exception:
                logger.exception('Could not remove orphaned account upload %s', name)


def erase_account_and_content(user):
    """Delete an account and its cascading records, then remove orphaned files."""
    using = router.db_for_write(type(user), instance=user)
    collector = Collector(using=using)
    collector.collect([user])
    files, collected_ids = _collect_files(collector)
    with transaction.atomic(using=using):
        collector.delete()
        transaction.on_commit(
            lambda: _delete_unreferenced_files(files, collected_ids),
            using=using,
        )


def anonymize_account_keep_content(user):
    """Disable sign-in and remove direct profile/security data, retaining authored content."""
    User = get_user_model()
    using = router.db_for_write(User, instance=user)
    profile_files = []
    for field_name in ('profile_pic', 'cover_photo'):
        value = getattr(user, field_name, None)
        if value and value.name and value.name != 'profile_pic/default_pic1.jpg':
            field = User._meta.get_field(field_name)
            profile_files.append((field.storage, value.name))

    with transaction.atomic(using=using):
        # Remove account-only security, connection, and preference records.
        from users.models import Block, DeviceAccount, Follow, HiddenAuthor, Pinch, PlatformInvite, RecoveryCode, UserProfilePhotoLike, UserSession, UserTwoFactor
        from posts.models import AuthorPreference, CommentLike, Like, Report
        from notifications.models import PushSubscription
        from groups.models import Membership
        from notifications.models import NotificationObject

        Block.objects.using(using).filter(blocker=user).delete()
        Block.objects.using(using).filter(blocked=user).delete()
        Follow.objects.using(using).filter(follower=user).delete()
        Follow.objects.using(using).filter(followed=user).delete()
        HiddenAuthor.objects.using(using).filter(hider=user).delete()
        HiddenAuthor.objects.using(using).filter(hidden_author=user).delete()
        Pinch.objects.using(using).filter(pinch_user=user).delete()
        Pinch.objects.using(using).filter(pinched_user=user).delete()
        UserProfilePhotoLike.objects.using(using).filter(user=user).delete()
        UserSession.objects.using(using).filter(user=user).delete()
        DeviceAccount.objects.using(using).filter(user=user).delete()
        RecoveryCode.objects.using(using).filter(user=user).delete()
        UserTwoFactor.objects.using(using).filter(user=user).delete()
        PushSubscription.objects.using(using).filter(user=user).delete()
        Membership.objects.using(using).filter(user=user).delete()
        PlatformInvite.objects.using(using).filter(inviter=user).delete()
        NotificationObject.objects.using(using).filter(recipient=user).delete()
        AuthorPreference.objects.using(using).filter(user=user).delete()
        AuthorPreference.objects.using(using).filter(author=user).delete()
        Like.objects.using(using).filter(user=user).delete()
        CommentLike.objects.using(using).filter(user=user).delete()
        Report.objects.using(using).filter(reporter=user).delete()

        user.username = f'deleted-user-{user.pk}-{uuid.uuid4().hex[:8]}'
        user.first_name = ''
        user.second_name = ''
        user.last_name = ''
        user.email = ''
        user.year = None
        user.course = None
        user.programme = None
        user.academic_level = None
        user.academic_year = None
        user.semester = None
        user.profile_pic = 'profile_pic/default_pic1.jpg'
        user.cover_photo = None
        user.bio = ''
        user.headline = ''
        user.interests = ''
        user.skills = []
        user.projects = []
        user.collaboration_status = ''
        user.github_url = ''
        user.linkedin_url = ''
        user.portfolio_url = ''
        user.twitter_url = ''
        user.profile_privacy = 'PRIVATE'
        user.is_active = False
        user.is_online = False
        user.set_unusable_password()
        user.save()

        transaction.on_commit(
            lambda: _delete_unreferenced_files(profile_files, {User: {user.pk}}),
            using=using,
        )
