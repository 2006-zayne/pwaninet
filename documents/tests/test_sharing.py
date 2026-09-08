"""Unit tests for document social sharing to profiles and groups."""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from documents.models import Category, Document
from documents.engagement.models import DocumentShare
from groups.models import Group, Membership, MembershipRole, MembershipStatus
from posts.models import Post

User = get_user_model()


class DocumentSharingTests(TestCase):
    """Test document sharing to profile, group, and copy link."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='sharinguser',
            email='sharing@example.com',
            password='password123'
        )
        self.non_member = User.objects.create_user(
            username='nonmember',
            email='nonmember@example.com',
            password='password123'
        )

        self.category = Category.objects.create(
            code='lecture_notes',
            name='Lecture Notes',
            is_active=True
        )

        self.document = Document.objects.create(
            title='Calculus II Notes',
            description='Detailed calculus notes',
            category=self.category,
            uploaded_by=self.user,
            status='ready',
            visibility='public'
        )

        self.group = Group.objects.create(
            name='Math Study Club',
            description='Group for math students'
        )

        # Approved membership
        Membership.objects.create(
            user=self.user,
            group=self.group,
            role=MembershipRole.MEMBER,
            status=MembershipStatus.APPROVED
        )

        self.group_member = User.objects.create_user(
            username='groupmember',
            email='member@example.com',
            password='password123'
        )
        Membership.objects.create(
            user=self.group_member,
            group=self.group,
            role=MembershipRole.MEMBER,
            status=MembershipStatus.APPROVED
        )

        self.pending_group = Group.objects.create(
            name='Physics Study Club',
            description='Group for physics students'
        )
        # Pending membership
        Membership.objects.create(
            user=self.user,
            group=self.pending_group,
            role=MembershipRole.MEMBER,
            status=MembershipStatus.PENDING
        )

        self.friend = User.objects.create_user(
            username='frienduser',
            email='friend@example.com',
            password='password123'
        )
        from users.models import Follow
        Follow.objects.create(follower=self.friend, followed=self.user)

        self.client = Client()

    def test_share_copy_link(self):
        """Sharing via copy link records DocumentShare and returns URL."""
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('documents:share_document', kwargs={'share_id': self.document.share_id}),
            {'share_type': 'copy_link'}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn(str(self.document.id), data['url'])
        self.assertTrue(DocumentShare.objects.filter(document=self.document, platform='copy_link').exists())

    def test_share_to_profile(self):
        """Sharing to profile creates a Post with shared_document and records share, without gradient and notifying friends."""
        from notifications.models import NotificationObject
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('documents:share_document', kwargs={'share_id': self.document.share_id}),
            {'share_type': 'profile'}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

        post = Post.objects.filter(author=self.user, shared_document=self.document).first()
        self.assertIsNotNone(post)
        self.assertIn(self.document.title, post.content)
        self.assertIsNone(post.group)
        self.assertEqual(post.gradient_class, 'none')
        self.assertTrue(DocumentShare.objects.filter(document=self.document, platform='profile').exists())

        # Verify notification sent to friend
        notification = NotificationObject.objects.filter(
            recipient=self.friend,
            notification_type='DOCUMENT_SHARED'
        ).first()
        self.assertIsNotNone(notification)
        self.assertEqual(
            notification.title,
            f"{self.user.username} shared a document to view: {self.document.title}"
        )
        self.assertTrue(notification.metadata.get('is_document_share'))
        self.assertEqual(notification.metadata.get('document_title'), self.document.title)

        # Verify rendered notification card content
        from notifications.rendering import render_notification
        html = render_notification(notification)
        self.assertIn("New documents from people you follow", html)
        self.assertIn(f"{self.user.username} shared a document to view: {self.document.title}", html)
        self.assertNotIn("shared a post with you", html)

    def test_share_to_group_as_approved_member(self):
        """Approved member can share document to group, creating group Post."""
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('documents:share_document', kwargs={'share_id': self.document.share_id}),
            {'share_type': 'group', 'group_id': self.group.id}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

        post = Post.objects.filter(author=self.user, group=self.group, shared_document=self.document).first()
        self.assertIsNotNone(post)
        self.assertEqual(post.group, self.group)
        self.assertEqual(post.gradient_class, 'none')
        self.assertTrue(DocumentShare.objects.filter(document=self.document, platform='group').exists())

        # Verify group member receives DOCUMENT_SHARED notification with group context
        from notifications.models import NotificationObject
        notif = NotificationObject.objects.filter(
            recipient=self.group_member,
            notification_type='DOCUMENT_SHARED'
        ).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.context_type, 'GROUP')
        self.assertEqual(notif.context_id, str(self.group.id))
        self.assertEqual(
            notif.title,
            f"{self.user.username} shared a document to view: {self.document.title}"
        )

    def test_share_to_group_as_non_member_rejected(self):
        """Non-member cannot share document to group (returns 403 Forbidden)."""
        self.client.force_login(self.non_member)
        response = self.client.post(
            reverse('documents:share_document', kwargs={'share_id': self.document.share_id}),
            {'share_type': 'group', 'group_id': self.group.id}
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Post.objects.filter(author=self.non_member, group=self.group).exists())

    def test_share_to_non_existent_group(self):
        """Sharing to non-existent group returns 404 Not Found."""
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('documents:share_document', kwargs={'share_id': self.document.share_id}),
            {'share_type': 'group', 'group_id': 99999}
        )
        self.assertEqual(response.status_code, 404)

    def test_share_invalid_share_type(self):
        """Invalid share_type returns 400 Bad Request."""
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('documents:share_document', kwargs={'share_id': self.document.share_id}),
            {'share_type': 'invalid_type'}
        )
        self.assertEqual(response.status_code, 400)

    def test_user_groups_for_sharing_endpoint(self):
        """user_groups_for_sharing returns only approved groups for the user."""
        self.client.force_login(self.user)
        response = self.client.get(reverse('documents:user_groups_for_sharing'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('groups', data)
        group_ids = [g['id'] for g in data['groups']]
        self.assertIn(self.group.id, group_ids)
        self.assertNotIn(self.pending_group.id, group_ids)
