"""
Notification Rules for PwaniNet Notification Engine v2

This module defines notification rules that transform platform events into user notifications.
Following the specification, each rule has: trigger, conditions, recipients, priority, category, delivery policy, aggregation policy.
"""
from dataclasses import dataclass
from typing import List, Callable, Optional, Dict, Any
from enum import Enum
from django.contrib.auth import get_user_model

User = get_user_model()


class AggregationPolicy(Enum):
    """Aggregation policy for notifications."""
    NEVER = "NEVER"
    ALLOWED = "ALLOWED"
    REQUIRED = "REQUIRED"


@dataclass
class NotificationRule:
    """
    A notification rule definition.
    
    Rules are evaluated against platform events to determine:
    - Whether a notification should be created
    - Who should receive it
    - Its priority, category, and policies
    """
    # Rule identification
    name: str
    trigger: str  # Event type that triggers this rule
    
    # Notification properties (no defaults)
    notification_type: str
    category: str
    priority: str
    recipients: Callable[[Dict[str, Any]], List[int]]  # Returns list of user IDs
    
    # Rule evaluation (with default)
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    
    # Policies (with defaults)
    delivery_policy: str = "IMMEDIATE"
    aggregation_policy: str = "ALLOWED"
    
    # Title and summary generation (with default)
    title_template: Optional[str] = None
    summary_template: Optional[str] = None
    
    # Action generation (with default)
    actions: Optional[Callable[[Dict[str, Any]], List[Dict[str, Any]]]] = None


# ============================================================================
# Recipient Resolution Functions
# ============================================================================

def _post_owner_recipient(event_data: Dict[str, Any]) -> List[int]:
    """Recipient: Post owner."""
    from posts.models import Post
    
    # For comment events, the post ID is in context_id, not target_id
    context_id = event_data.get('context_id')
    target_type = event_data.get('target_type')
    
    post_id = None
    if target_type == 'Comment' and context_id:
        post_id = context_id
    else:
        post_id = event_data.get('target_id')
    
    if not post_id:
        return []
    
    try:
        post = Post.objects.get(id=post_id)
        return [post.author.id]
    except Post.DoesNotExist:
        return []


def _comment_author_recipient(event_data: Dict[str, Any]) -> List[int]:
    """Recipient: Comment author."""
    from posts.models import Comment
    
    target_id = event_data.get('target_id')
    if not target_id:
        return []
    
    try:
        comment = Comment.objects.get(id=target_id)
        return [comment.author.id]
    except Comment.DoesNotExist:
        return []


def _parent_comment_author_recipient(event_data: Dict[str, Any]) -> List[int]:
    """Recipient: Parent comment author."""
    from posts.models import Comment
    
    target_id = event_data.get('target_id')
    if not target_id:
        return []
    
    try:
        comment = Comment.objects.get(id=target_id)
        if comment.parent_comment:
            return [comment.parent_comment.author.id]
        return []
    except Comment.DoesNotExist:
        return []


def _group_admins_recipient(event_data: Dict[str, Any]) -> List[int]:
    """Recipient: Group admins."""
    from groups.models import Membership, MembershipRole, MembershipStatus
    
    target_id = event_data.get('target_id')
    if not target_id:
        return []
    
    try:
        admin_memberships = Membership.objects.filter(
            group_id=target_id,
            role=MembershipRole.ADMIN,
            status=MembershipStatus.APPROVED
        ).select_related('user')
        return [m.user.id for m in admin_memberships]
    except Exception:
        return []


def _group_member_recipient(event_data: Dict[str, Any]) -> List[int]:
    """Recipient: Specific group member from context."""
    context_id = event_data.get('context_id')
    if not context_id:
        return []
    
    try:
        user = User.objects.get(id=context_id)
        return [user.id]
    except User.DoesNotExist:
        return []


def _followed_user_recipient(event_data: Dict[str, Any]) -> List[int]:
    """Recipient: User who was followed."""
    target_id = event_data.get('target_id')
    if not target_id:
        return []
    
    try:
        user = User.objects.get(id=target_id)
        return [user.id]
    except User.DoesNotExist:
        return []


def _followers_of_author_recipient(event_data: Dict[str, Any]) -> List[int]:
    """Recipient: Users who follow the post author (for new post notifications)."""
    actor_id = event_data.get('actor_id')
    group_id = event_data.get('context_id')  # This will be set if post is in a group
    
    if not actor_id:
        return []
    
    try:
        author = User.objects.get(id=actor_id)
        
        if group_id:
            # For group posts, send to group members
            from groups.models import Membership, MembershipStatus
            return list(Membership.objects.filter(
                group_id=group_id,
                status=MembershipStatus.APPROVED
            ).exclude(user_id=actor_id).values_list('user_id', flat=True))
        else:
            # For global posts, send to users who follow the author
            # following_relationships are relationships where the user is the follower
            return list(User.objects.filter(
                following_relationships__followed=author
            ).exclude(id=actor_id).values_list('id', flat=True))
    except User.DoesNotExist:
        return []


def _pinched_user_recipient(event_data: Dict[str, Any]) -> List[int]:
    """Recipient: User who was pinched."""
    target_id = event_data.get('target_id')
    if not target_id:
        return []
    
    try:
        user = User.objects.get(id=target_id)
        return [user.id]
    except User.DoesNotExist:
        return []


def _post_sharer_recipient(event_data: Dict[str, Any]) -> List[int]:
    """Recipient: User who received the shared post."""
    # Get recipient from metadata (recipient_id) or audience field
    metadata = event_data.get('metadata', {})
    recipient_id = metadata.get('recipient_id')
    
    if recipient_id:
        try:
            user = User.objects.get(id=int(recipient_id))
            return [user.id]
        except (User.DoesNotExist, ValueError):
            return []
    
    # Fallback to audience field
    audience = event_data.get('audience')
    if audience:
        try:
            user = User.objects.get(id=int(audience))
            return [user.id]
        except (User.DoesNotExist, ValueError):
            return []
    
    return []


def _original_post_author_recipient(event_data: Dict[str, Any]) -> List[int]:
    """Recipient: Original post author (for reposts)."""
    from posts.models import Post
    
    target_id = event_data.get('target_id')
    if not target_id:
        return []
    
    try:
        post = Post.objects.get(id=target_id)
        return [post.author.id]
    except Post.DoesNotExist:
        return []


def _parent_comment_author_not_self_condition(event_data: Dict[str, Any]) -> bool:
    """Condition: Only notify if actor is not the parent comment author."""
    actor_id = event_data.get('actor_id')
    parent_comment_id = event_data.get('target_id')
    
    if not actor_id or not parent_comment_id:
        return False
    
    try:
        from posts.models import Comment
        parent_comment = Comment.objects.get(id=parent_comment_id)
        return int(actor_id) != parent_comment.author.id
    except Comment.DoesNotExist:
        return False


def _parent_comment_author_recipient(event_data: Dict[str, Any]) -> List[int]:
    """Recipient: Parent comment author (for comment replies)."""
    from posts.models import Comment
    
    target_id = event_data.get('target_id')
    if not target_id:
        return []
    
    try:
        parent_comment = Comment.objects.get(id=target_id)
        return [parent_comment.author.id]
    except Comment.DoesNotExist:
        return []


def _comment_author_recipient(event_data: Dict[str, Any]) -> List[int]:
    """Recipient: Comment author (for comment likes)."""
    from posts.models import Comment
    
    target_id = event_data.get('target_id')
    if not target_id:
        return []
    
    try:
        comment = Comment.objects.get(id=target_id)
        return [comment.author.id]
    except Comment.DoesNotExist:
        return []


def _document_owner_recipient(event_data: Dict[str, Any]) -> List[int]:
    """Recipient: Document owner."""
    from documents.documents.models import Document
    
    target_id = event_data.get('target_id')
    if not target_id:
        return []
    
    try:
        document = Document.objects.get(id=target_id)
        return [document.uploaded_by.id]
    except Document.DoesNotExist:
        return []


def _course_creator_recipient(event_data: Dict[str, Any]) -> List[int]:
    """Recipient: Course creator."""
    from courses.models import Course
    
    target_id = event_data.get('target_id')
    if not target_id:
        return []
    
    try:
        course = Course.objects.get(id=target_id)
        return [course.created_by.id]
    except Course.DoesNotExist:
        return []


def _course_members_recipient(event_data: Dict[str, Any]) -> List[int]:
    """Recipient: All members of a course."""
    from courses.models import Course
    
    context_id = event_data.get('context_id')
    if not context_id:
        return []
    
    try:
        course = Course.objects.get(id=context_id)
        # Get all enrolled students in the course
        enrolled_users = course.enrolled_users.all()
        return [user.id for user in enrolled_users]
    except Course.DoesNotExist:
        return []


def _academic_unit_members_recipient(event_data: Dict[str, Any]) -> List[int]:
    """Recipient: All members of an academic unit (for document uploads)."""
    from documents.documents.models import AcademicUnit
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    context_id = event_data.get('context_id')
    if not context_id:
        return []
    
    try:
        academic_unit = AcademicUnit.objects.get(id=context_id)
        # Get all users enrolled in courses that include this academic unit
        from courses.models import CourseAcademicUnit
        course_academic_units = CourseAcademicUnit.objects.filter(academic_unit=academic_unit)
        enrolled_users = set()
        for cau in course_academic_units:
            # Find users enrolled in this course
            enrolled_users.update(
                User.objects.filter(course=cau.course).values_list('id', flat=True)
            )
        return list(enrolled_users)
    except AcademicUnit.DoesNotExist:
        return []


def _message_recipient_recipient(event_data: Dict[str, Any]) -> List[int]:
    """Recipient: Message recipient."""
    from messaging.frozen.models import Message
    
    target_id = event_data.get('target_id')
    if not target_id:
        return []
    
    try:
        message = Message.objects.get(id=target_id)
        # Get conversation members except the sender
        conversation_members = message.conversation.members.exclude(
            id=message.sender.id
        )
        return [m.id for m in conversation_members]
    except Message.DoesNotExist:
        return []


def _conversation_member_recipient(event_data: Dict[str, Any]) -> List[int]:
    """Recipient: Added conversation member."""
    context_id = event_data.get('context_id')
    if not context_id:
        return []
    
    try:
        user = User.objects.get(id=context_id)
        return [user.id]
    except User.DoesNotExist:
        return []


# ============================================================================
# Condition Functions
# ============================================================================

def _post_author_not_self_condition(event_data: Dict[str, Any]) -> bool:
    """Condition: Actor is not the post author and it's not a reply."""
    actor_id = event_data.get('actor_id')
    post_author_id = event_data.get('post_author_id')
    parent_comment_id = event_data.get('parent_comment_id')
    
    # Exclude replies (they should be handled by POST_COMMENT_REPLY_RULE)
    if parent_comment_id:
        return False
    
    return actor_id != post_author_id


def _actor_not_recipient_condition(event_data: Dict[str, Any]) -> bool:
    """Condition: Actor is not the recipient."""
    actor_id = event_data.get('actor_id')
    recipient_ids = event_data.get('recipient_user_ids', [])
    return actor_id not in recipient_ids


# Posts Rules
POST_LIKE_RULE = NotificationRule(
    name="post_like",
    trigger="posts.post.liked",
    condition=_post_author_not_self_condition,
    notification_type="LIKE",
    category="SOCIAL",
    priority="LOW",
    delivery_policy="IMMEDIATE",
    aggregation_policy="ALLOWED",
    recipients=_post_owner_recipient,
    title_template="{actor_username} liked your post",
    summary_template="Your post received new likes",
    actions=lambda event: [
        {
            'action_type': 'VIEW',
            'label': 'View Post',
            'url': f"/post/{event.get('target_id')}",
            'method': 'GET',
            'is_primary': True,
            'order': 0,
            'style': 'primary'
        }
    ]
)

POST_COMMENT_RULE = NotificationRule(
    name="post_comment",
    trigger="posts.comment.created",
    condition=_post_author_not_self_condition,
    notification_type="COMMENT",
    category="SOCIAL",
    priority="NORMAL",
    delivery_policy="IMMEDIATE",
    aggregation_policy="ALLOWED",
    recipients=_post_owner_recipient,
    title_template="{actor_username} commented on your post",
    summary_template="Your post has new comments"
)

POST_COMMENT_REPLY_RULE = NotificationRule(
    name="post_comment_reply",
    trigger="posts.comment.replied",
    condition=_parent_comment_author_not_self_condition,
    notification_type="COMMENT_REPLY",
    category="SOCIAL",
    priority="NORMAL",
    delivery_policy="IMMEDIATE",
    aggregation_policy="ALLOWED",
    recipients=_parent_comment_author_recipient,
    title_template="{actor_username} replied to your comment",
    summary_template="Your comment has new replies"
)

COMMENT_LIKED_RULE = NotificationRule(
    name="comment_liked",
    trigger="posts.comment.liked",
    condition=None,
    notification_type="COMMENT_LIKE",
    category="SOCIAL",
    priority="LOW",
    delivery_policy="IMMEDIATE",
    aggregation_policy="ALLOWED",
    recipients=_comment_author_recipient,
    title_template="{actor_username} liked your comment",
    summary_template="Your comment received likes"
)

POST_SHARED_RULE = NotificationRule(
    name="post_shared",
    trigger="posts.post.shared",
    condition=None,
    notification_type="SHARE",
    category="SOCIAL",
    priority="NORMAL",
    delivery_policy="IMMEDIATE",
    aggregation_policy="ALLOWED",
    recipients=_post_sharer_recipient,
    title_template="{actor_username} shared your post",
    summary_template="Your post was shared"
)

POST_SHARED_TO_GROUP_RULE = NotificationRule(
    name="post_shared_to_group",
    trigger="posts.post.shared_to_group",
    condition=None,
    notification_type="SHARE",
    category="SOCIAL",
    priority="NORMAL",
    delivery_policy="IMMEDIATE",
    aggregation_policy="ALLOWED",
    recipients=_group_member_recipient,
    title_template="{actor_username} shared a post to the group",
    summary_template="New post shared to group"
)

POST_REPORTED_RULE = NotificationRule(
    name="post_reported",
    trigger="posts.post.reported",
    condition=None,
    notification_type="SECURITY",
    category="SECURITY",
    priority="HIGH",
    delivery_policy="IMMEDIATE",
    aggregation_policy="NEVER",
    recipients=lambda event_data: [int(event_data.get('audience', 0))] if event_data.get('audience') else [],
    title_template="Post reported: {report_reason}",
    summary_template="New post report",
)

POST_REPOSTED_RULE = NotificationRule(
    name="post_reposted",
    trigger="posts.post.reposted",
    condition=None,
    notification_type="POST_REPOSTED",
    category="SOCIAL",
    priority="NORMAL",
    delivery_policy="IMMEDIATE",
    aggregation_policy="ALLOWED",
    recipients=_original_post_author_recipient,
    title_template="{actor_username} reposted your post",
    summary_template="Your post was reposted"
)

POST_CREATED_RULE = NotificationRule(
    name="post_created",
    trigger="posts.post.created",
    condition=None,
    notification_type="POST_CREATED",
    category="SOCIAL",
    priority="NORMAL",
    delivery_policy="IMMEDIATE",
    aggregation_policy="ALLOWED",
    recipients=_followers_of_author_recipient,
    title_template="{actor_username} posted a new update",
    summary_template="New post from someone you follow"
)

# Groups Rules
GROUP_INVITE_RULE = NotificationRule(
    name="group_invite",
    trigger="groups.member.invited",
    condition=None,
    notification_type="INVITE",
    category="WORKSPACE",
    priority="HIGH",
    delivery_policy="IMMEDIATE",
    aggregation_policy="NEVER",
    recipients=_group_member_recipient,
    title_template="You have been invited to join {group_name}",
    summary_template="Group invitation pending",
    actions=lambda event: [
        {
            'action_type': 'ACCEPT',
            'label': 'Accept',
            'url': f"/groups/invite/respond/{event.get('notification_id')}/accept/",
            'method': 'POST',
            'is_primary': True,
            'order': 0
        },
        {
            'action_type': 'DECLINE',
            'label': 'Decline',
            'url': f"/groups/invite/respond/{event.get('notification_id')}/decline/",
            'method': 'POST',
            'is_primary': False,
            'order': 1
        }
    ]
)

GROUP_REQUEST_RULE = NotificationRule(
    name="group_request",
    trigger="groups.member.requested",
    condition=None,
    notification_type="GROUP",
    category="WORKSPACE",
    priority="HIGH",
    delivery_policy="IMMEDIATE",
    aggregation_policy="ALLOWED",
    recipients=_group_admins_recipient,
    title_template="{actor_username} requested to join {group_name}",
    summary_template="New group join request",
    actions=lambda event: [
        {
            'action_type': 'REVIEW',
            'label': 'Review Request',
            'url': f"/groups/{event.get('group_id')}/requests",
            'method': 'GET',
            'is_primary': True,
            'order': 0
        }
    ]
)

GROUP_APPROVED_RULE = NotificationRule(
    name="group_approved",
    trigger="groups.member.approved",
    condition=None,
    notification_type="GROUP",
    category="WORKSPACE",
    priority="HIGH",
    delivery_policy="IMMEDIATE",
    aggregation_policy="NEVER",
    recipients=_group_member_recipient,
    title_template="You have been approved to join {group_name}",
    summary_template="Group membership approved"
)

GROUP_REJECTED_RULE = NotificationRule(
    name="group_rejected",
    trigger="groups.member.rejected",
    condition=None,
    notification_type="GROUP",
    category="WORKSPACE",
    priority="NORMAL",
    delivery_policy="IMMEDIATE",
    aggregation_policy="NEVER",
    recipients=_group_member_recipient,
    title_template="Your request to join {group_name} was declined",
    summary_template="Group membership request declined"
)

# Users Rules
USER_FOLLOW_RULE = NotificationRule(
    name="user_follow",
    trigger="users.user.followed",
    condition=None,
    notification_type="FOLLOW",
    category="SOCIAL",
    priority="LOW",
    delivery_policy="IMMEDIATE",
    aggregation_policy="ALLOWED",
    recipients=_followed_user_recipient,
    title_template="{actor_username} started following you",
    summary_template="You have a new follower"
)

USER_PINCH_RULE = NotificationRule(
    name="user_pinch",
    trigger="users.user.pinched",
    condition=None,
    notification_type="PINCH",
    category="SOCIAL",
    priority="LOW",
    delivery_policy="IMMEDIATE",
    aggregation_policy="ALLOWED",
    recipients=_pinched_user_recipient,
    title_template="{actor_username} pinched your profile",
    summary_template="Your profile was pinched"
)

# Documents Rules
DOCUMENT_UPLOADED_RULE = NotificationRule(
    name="document_uploaded",
    trigger="documents.document.uploaded",
    condition=None,
    notification_type="DOCUMENT",
    category="DOCUMENT",
    priority="NORMAL",
    delivery_policy="IMMEDIATE",
    aggregation_policy="ALLOWED",
    recipients=_academic_unit_members_recipient,
    title_template="{actor_username} uploaded a new document to your academic unit",
    summary_template="New document available in {academic_unit_code}"
)

DOCUMENT_PUBLISHED_RULE = NotificationRule(
    name="document_published",
    trigger="documents.document.published",
    condition=None,
    notification_type="DOCUMENT",
    category="DOCUMENT",
    priority="NORMAL",
    delivery_policy="IMMEDIATE",
    aggregation_policy="ALLOWED",
    recipients=_document_owner_recipient,
    title_template="{actor_username} published a document",
    summary_template="Document published"
)

DOCUMENT_DOWNLOADED_RULE = NotificationRule(
    name="document_downloaded",
    trigger="documents.document.downloaded",
    condition=None,
    notification_type="DOCUMENT",
    category="DOCUMENT",
    priority="LOW",
    delivery_policy="IMMEDIATE",
    aggregation_policy="ALLOWED",
    recipients=_document_owner_recipient,
    title_template="{actor_username} downloaded your document",
    summary_template="Your document was downloaded"
)

DOCUMENT_BOOKMARKED_RULE = NotificationRule(
    name="document_bookmarked",
    trigger="documents.document.bookmarked",
    condition=None,
    notification_type="DOCUMENT",
    category="DOCUMENT",
    priority="LOW",
    delivery_policy="IMMEDIATE",
    aggregation_policy="ALLOWED",
    recipients=_document_owner_recipient,
    title_template="{actor_username} bookmarked your document",
    summary_template="Your document was bookmarked"
)

DOCUMENT_RATED_RULE = NotificationRule(
    name="document_rated",
    trigger="documents.document.rated",
    condition=None,
    notification_type="DOCUMENT",
    category="DOCUMENT",
    priority="LOW",
    delivery_policy="IMMEDIATE",
    aggregation_policy="ALLOWED",
    recipients=_document_owner_recipient,
    title_template="{actor_username} rated your document",
    summary_template="Your document was rated"
)

# Courses Rules
COURSE_CREATED_RULE = NotificationRule(
    name="course_created",
    trigger="courses.course.created",
    condition=None,
    notification_type="WORKSPACE",
    category="ACADEMIC",
    priority="NORMAL",
    delivery_policy="IMMEDIATE",
    aggregation_policy="ALLOWED",
    recipients=_course_creator_recipient,
    title_template="{actor_username} created a new course",
    summary_template="New course created"
)

UNIT_CREATED_RULE = NotificationRule(
    name="unit_created",
    trigger="courses.unit.created",
    condition=None,
    notification_type="WORKSPACE",
    category="ACADEMIC",
    priority="NORMAL",
    delivery_policy="IMMEDIATE",
    aggregation_policy="ALLOWED",
    recipients=_course_creator_recipient,
    title_template="{actor_username} created a new unit",
    summary_template="New unit created"
)

# Messaging Rules
MESSAGE_SENT_RULE = NotificationRule(
    name="message_sent",
    trigger="messaging.message.sent",
    condition=None,
    notification_type="WORKSPACE",
    category="WORKSPACE",
    priority="HIGH",
    delivery_policy="IMMEDIATE",
    aggregation_policy="NEVER",
    recipients=_message_recipient_recipient,
    title_template="{actor_username} sent you a message",
    summary_template="New message"
)

CONVERSATION_MEMBER_ADDED_RULE = NotificationRule(
    name="conversation_member_added",
    trigger="messaging.conversation.member_added",
    condition=None,
    notification_type="WORKSPACE",
    category="WORKSPACE",
    priority="NORMAL",
    delivery_policy="IMMEDIATE",
    aggregation_policy="ALLOWED",
    recipients=_conversation_member_recipient,
    title_template="{actor_username} added you to a conversation",
    summary_template="Added to conversation"
)

# Courses Rules
COURSE_ASSIGNMENT_PUBLISHED_RULE = NotificationRule(
    name="course_assignment_published",
    trigger="courses.assignment.published",
    condition=None,
    notification_type="ASSIGNMENT",
    category="ACADEMIC",
    priority="HIGH",
    delivery_policy="IMMEDIATE",
    aggregation_policy="NEVER",
    recipients=_group_member_recipient,
    title_template="New assignment available: {assignment_title}",
    summary_template="{course_name} - {assignment_title}",
    actions=lambda event: [
        {
            'action_type': 'OPEN',
            'label': 'Open Assignment',
            'url': f"/courses/{event.get('course_id')}/assignments/{event.get('assignment_id')}",
            'method': 'GET',
            'is_primary': True,
            'order': 0
        }
    ]
)

def _all_users_recipient(event_data: Dict[str, Any]) -> List[int]:
    """Recipient: All users (for system-wide announcements like releases)."""
    return list(User.objects.filter(is_active=True).values_list('id', flat=True))


# ============================================================================
# Release Rules
# ============================================================================

RELEASE_PUBLISHED_RULE = NotificationRule(
    name="release_published",
    trigger="releases.release.published",
    condition=None,
    notification_type="RELEASE",
    category="SYSTEM",
    priority="HIGH",
    delivery_policy="IMMEDIATE",
    aggregation_policy="NEVER",
    recipients=_all_users_recipient,
    title_template="New version {version} is now available",
    summary_template="New release available",
    actions=lambda event: [
        {
            'action_type': 'SEE_WHATS_NEW',
            'label': "See What's New",
            'url': f"/system/releases/{event.get('target_id')}/",
            'method': 'GET',
            'is_primary': True,
            'order': 0,
            'style': 'primary'
        }
    ]
)


# All rules registry
RULES_REGISTRY = [
    POST_LIKE_RULE,
    POST_COMMENT_RULE,
    POST_COMMENT_REPLY_RULE,
    COMMENT_LIKED_RULE,
    POST_SHARED_RULE,
    POST_SHARED_TO_GROUP_RULE,
    POST_REPORTED_RULE,
    POST_REPOSTED_RULE,
    POST_CREATED_RULE,
    GROUP_INVITE_RULE,
    GROUP_REQUEST_RULE,
    GROUP_APPROVED_RULE,
    GROUP_REJECTED_RULE,
    USER_FOLLOW_RULE,
    USER_PINCH_RULE,
    DOCUMENT_UPLOADED_RULE,
    DOCUMENT_PUBLISHED_RULE,
    DOCUMENT_DOWNLOADED_RULE,
    DOCUMENT_BOOKMARKED_RULE,
    DOCUMENT_RATED_RULE,
    COURSE_CREATED_RULE,
    UNIT_CREATED_RULE,
    MESSAGE_SENT_RULE,
    CONVERSATION_MEMBER_ADDED_RULE,
    COURSE_ASSIGNMENT_PUBLISHED_RULE,
    RELEASE_PUBLISHED_RULE,
]


def get_rules_for_event(event_type: str) -> List[NotificationRule]:
    """Get all rules that match a given event type."""
    return [rule for rule in RULES_REGISTRY if rule.trigger == event_type]


def get_all_rules() -> List[NotificationRule]:
    """Get all registered rules."""
    return RULES_REGISTRY
