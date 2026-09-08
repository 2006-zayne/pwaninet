from django.db import models
from django.conf import settings
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex, OpClass


class JoinPolicy(models.TextChoices):
    OPEN = "open", "Open"
    APPROVAL = "approval", "Requires Approval"
    INVITE_ONLY = "invite", "Invite Only"


class PostVisibility(models.TextChoices):
    EVERYONE = "everyone", "Everyone in Pwaninet"
    MEMBERS_ONLY = "members_only", "Only Members"


class EditPermission(models.TextChoices):
    ADMINS_ONLY = "admins_only", "Admins Only"
    ADMINS_MODERATORS = "admins_moderators", "Admins and Moderators"


class InvitePermission(models.TextChoices):
    ADMINS_ONLY = "admins_only", "Admins Only"
    ALL_MEMBERS = "all_members", "All Members"


class Group(models.Model):
    name = models.CharField(max_length=200, unique=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_groups')
    description = models.TextField(max_length=500, blank=True)
    group_pic = models.ImageField(upload_to='group_profile_pic', null=True, blank=True)
    cover_photo = models.ImageField(upload_to='group_covers/', blank=True, null=True)
    is_official = models.BooleanField(default=False)
    auto_join_on_signup = models.BooleanField(default=False, help_text="Automatically enroll new users matching course/year into this group")
    join_policy = models.CharField(
        max_length=20,
        choices=JoinPolicy.choices,
        default=JoinPolicy.OPEN
    )
    post_visibility = models.CharField(
        max_length=20,
        choices=PostVisibility.choices,
        default=PostVisibility.MEMBERS_ONLY,
        help_text="Who can view group posts in the main feed"
    )
    edit_permission = models.CharField(
        max_length=30,
        choices=EditPermission.choices,
        default=EditPermission.ADMINS_ONLY,
        help_text="Who can edit group details"
    )
    invite_permission = models.CharField(
        max_length=30,
        choices=InvitePermission.choices,
        default=InvitePermission.ADMINS_ONLY,
        help_text="Who can invite users to the group"
    )
    course = models.ForeignKey('courses.Course', on_delete=models.SET_NULL, null=True, blank=True)
    year = models.ForeignKey('courses.Year', on_delete=models.SET_NULL, null=True, blank=True)
    programme = models.ForeignKey('documents.Programme', on_delete=models.SET_NULL, null=True, blank=True, related_name='groups')
    academic_level = models.ForeignKey('documents.AcademicLevel', on_delete=models.SET_NULL, null=True, blank=True, related_name='groups')
    created_at = models.DateTimeField(auto_now_add=True)
    search_vector = SearchVectorField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            GinIndex(fields=['search_vector'], name='group_search_vector_idx'),
            GinIndex(
                OpClass('name', name='gin_trgm_ops'),
                name='group_name_trgm_idx',
            ),
        ]

    def update_search_vector(self):
        """Recompute search vector with field weights."""
        from django.contrib.postgres.search import SearchVector
        Group.objects.filter(pk=self.pk).update(
            search_vector=(
                SearchVector('name', weight='A') +
                SearchVector('description', weight='B')
            )
        )

    def __str__(self):
        return self.name
    
    @property
    def get_photo_url(self):
        if self.group_pic and hasattr(self.group_pic, 'url'):
            return self.group_pic.url
        return f"{settings.STATIC_URL}images/default_group.jpg"


class MembershipRole(models.TextChoices):
    ADMIN = 'ADMIN', 'Admin'
    MODERATOR = 'MODERATOR', 'Moderator'
    DELEGATE = 'DELEGATE', 'Delegate'
    MEMBER = 'MEMBER', 'Member'


class MembershipStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'


class Membership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='group_memberships', db_index=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='memberships', db_index=True)
    role = models.CharField(max_length=20, choices=MembershipRole.choices, default=MembershipRole.MEMBER, db_index=True)
    status = models.CharField(max_length=20, choices=MembershipStatus.choices, default=MembershipStatus.APPROVED, db_index=True)
    joined_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ('user', 'group')
        ordering = ['-joined_at']

    def __str__(self):
        return f"{self.user.username} - {self.group.name} ({self.role})"


# Clean domain alias
GroupMember = Membership


class JoinRequestStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    CANCELLED = 'CANCELLED', 'Cancelled'


class GroupJoinRequest(models.Model):
    """Inbound request from a user to join a group requiring approval"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='group_join_requests', db_index=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='join_requests', db_index=True)
    status = models.CharField(max_length=20, choices=JoinRequestStatus.choices, default=JoinRequestStatus.PENDING, db_index=True)
    message = models.TextField(blank=True, default='')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_group_requests')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'group'],
                condition=models.Q(status='PENDING'),
                name='unique_pending_group_join_request'
            )
        ]

    def __str__(self):
        return f"{self.user.username} -> {self.group.name} ({self.status})"


class InvitationStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    ACCEPTED = 'ACCEPTED', 'Accepted'
    DECLINED = 'DECLINED', 'Declined'
    REVOKED = 'REVOKED', 'Revoked'
    EXPIRED = 'EXPIRED', 'Expired'


class GroupInvitation(models.Model):
    """Outbound invitation for a user to join a group"""
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='invitations', db_index=True)
    inviter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_group_invitations', db_index=True)
    invitee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_group_invitations', db_index=True)
    status = models.CharField(max_length=20, choices=InvitationStatus.choices, default=InvitationStatus.PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['group', 'invitee'],
                condition=models.Q(status='PENDING'),
                name='unique_pending_group_invitation'
            )
        ]

    def __str__(self):
        return f"Invite: {self.inviter.username} -> {self.invitee.username} for {self.group.name} ({self.status})"

    @property
    def is_expired(self):
        from django.utils import timezone
        return self.expires_at < timezone.now()


class AnnouncementPriority(models.TextChoices):
    NORMAL = 'NORMAL', 'Normal'
    IMPORTANT = 'IMPORTANT', 'Important'
    URGENT = 'URGENT', 'Urgent'


class Announcement(models.Model):
    """Group announcements"""
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='announcements', db_index=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_announcements', db_index=True)
    title = models.CharField(max_length=200)
    content = models.TextField()
    priority = models.CharField(max_length=20, choices=AnnouncementPriority.choices, default=AnnouncementPriority.NORMAL, db_index=True)
    is_pinned = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']
        indexes = [
            models.Index(fields=['group', '-is_pinned', '-created_at']),
            models.Index(fields=['group', 'priority', '-created_at']),
            models.Index(fields=['author', '-created_at']),
        ]

    def __str__(self):
        return f"{self.title} - {self.group.name}"


class AnnouncementAttachment(models.Model):
    """Attachments for announcements"""
    
    ATTACHMENT_TYPE_CHOICES = [
        ('image', 'Image'),
        ('document', 'Document'),
    ]
    
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='attachments', db_index=True)
    attachment_type = models.CharField(max_length=20, choices=ATTACHMENT_TYPE_CHOICES, default='image')
    
    # For image attachments
    file = models.FileField(upload_to='announcements/attachments', blank=True, null=True)
    thumbnail = models.ImageField(upload_to='announcements/thumbnails', blank=True, null=True)
    
    # For document attachments (linked to document repository)
    document = models.ForeignKey('documents.Document', on_delete=models.CASCADE, related_name='announcement_attachments', blank=True, null=True)
    
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['announcement', '-uploaded_at']),
            models.Index(fields=['attachment_type']),
        ]

    def __str__(self):
        if self.attachment_type == 'document' and self.document:
            return f"{self.document.title} - {self.announcement.title}"
        return f"{self.file.name} - {self.announcement.title}"


class GroupPhotoLike(models.Model):
    """Likes for group profile and cover photos"""
    PHOTO_TYPE_CHOICES = [
        ('group', 'Group Photo'),
        ('cover', 'Cover Photo'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='group_photo_likes', db_index=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='photo_likes', db_index=True)
    photo_type = models.CharField(max_length=10, choices=PHOTO_TYPE_CHOICES, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ('user', 'group', 'photo_type')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['group', 'photo_type', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} likes {self.group.name}'s {self.photo_type} photo"


class GroupMessage(models.Model):
    """Messages in group chats"""
    MESSAGE_TYPE_CHOICES = [
        ('text', 'Text'),
        ('media_group', 'Media Group'),
        ('system', 'System'),
        ('audio', 'Audio'),
    ]

    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
    ]

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='messages', db_index=True)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_group_messages', db_index=True)
    content = models.TextField(blank=True, null=True)
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='text')
    reply_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['group', '-created_at']),
            models.Index(fields=['sender', '-created_at']),
            models.Index(fields=['group', 'status']),
        ]

    def __str__(self):
        return f"{self.sender.username} in {self.group.name}: {self.content[:50] if self.content else '[media]'}"


class GroupMessageAttachment(models.Model):
    """Attachments for group messages"""
    ATTACHMENT_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('document', 'Document'),
    ]

    message = models.ForeignKey(GroupMessage, on_delete=models.CASCADE, related_name='attachments', db_index=True)
    attachment_type = models.CharField(max_length=20, choices=ATTACHMENT_TYPE_CHOICES)
    file = models.FileField(upload_to='group_message_attachments/%Y/%m/%d/')
    thumbnail = models.ImageField(upload_to='group_message_thumbnails/%Y/%m/%d/', blank=True, null=True)
    caption = models.TextField(blank=True, null=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['message', 'order']),
        ]

    def __str__(self):
        return f"{self.attachment_type} for message {self.message.id}"


class GroupMessageReaction(models.Model):
    """Reactions to group messages"""
    EMOJI_CHOICES = [
        ('👍', 'Thumbs Up'),
        ('❤️', 'Heart'),
        ('😂', 'Laugh'),
        ('😮', 'Wow'),
        ('😢', 'Sad'),
        ('😡', 'Angry'),
    ]

    message = models.ForeignKey(GroupMessage, on_delete=models.CASCADE, related_name='reactions', db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='group_message_reactions', db_index=True)
    emoji = models.CharField(max_length=10, choices=EMOJI_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ('message', 'user', 'emoji')
        indexes = [
            models.Index(fields=['message', 'emoji']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} reacted {self.emoji} to message {self.message.id}"
