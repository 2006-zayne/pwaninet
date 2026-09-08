import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from groups.models import (
    Group, Membership, MembershipRole, MembershipStatus, JoinPolicy,
    InvitePermission, GroupJoinRequest, GroupInvitation, Announcement
)
from notifications.models import NotificationObject, NotificationAction
from notifications.rendering.adapters import NotificationObjectAdapter
from notifications.rendering.profile_registry import profile_registry
from notifications.rendering.message_engine import NotificationMessageEngine
from notifications.events import publish_event, EventTypes, EventSources, EventActions
from groups.services.group_notification_service import (
    send_group_join_request_notification,
    send_group_approved_notification,
    send_group_rejected_notification,
    send_group_welcome_notification,
    send_group_invite_notification,
)

User = get_user_model()


class GroupNotificationWiringTestCase(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin_boss',
            email='admin@example.com',
            password='password123'
        )
        self.applicant_user = User.objects.create_user(
            username='applicant_jane',
            email='jane@example.com',
            password='password123'
        )
        self.member_user = User.objects.create_user(
            username='member_bob',
            email='bob@example.com',
            password='password123'
        )
        self.group = Group.objects.create(
            name='Alpha Innovators',
            created_by=self.admin_user,
            join_policy=JoinPolicy.APPROVAL,
            invite_permission=InvitePermission.ALL_MEMBERS
        )
        # Add admin membership with _skip_signal_notification to mimic create_group_view
        m = Membership(
            group=self.group,
            user=self.admin_user,
            role=MembershipRole.ADMIN,
            status=MembershipStatus.APPROVED
        )
        m._skip_signal_notification = True
        m.save()
        self.adapter = NotificationObjectAdapter()

    def test_group_creator_does_not_receive_self_notification_on_creation(self):
        """Verify creator receives NO notification when group membership is saved."""
        initial_count = NotificationObject.objects.filter(recipient=self.admin_user).count()

        # Simulate normal post_save on membership for creator (without skip flag)
        new_group = Group.objects.create(
            name='Beta Coders',
            created_by=self.admin_user,
            join_policy=JoinPolicy.OPEN
        )
        Membership.objects.create(
            group=new_group,
            user=self.admin_user,
            role=MembershipRole.ADMIN,
            status=MembershipStatus.APPROVED
        )

        admin_notifs = NotificationObject.objects.filter(recipient=self.admin_user).count()
        self.assertEqual(admin_notifs, initial_count, "Admin/Creator must not receive notification when creating their own group")

    def test_join_request_notification_wiring_and_actions(self):
        """
        Verify join request creates GROUP_REQUEST for admin only, with Approve and Reject actions,
        and never a duplicate or self-notification to applicant.
        """
        send_group_join_request_notification(self.applicant_user, self.group)

        # 1. Applicant gets zero notifications
        applicant_notifs = NotificationObject.objects.filter(recipient=self.applicant_user)
        self.assertEqual(applicant_notifs.count(), 0)

        # 2. Admin gets exactly one GROUP_REQUEST notification
        admin_notifs = NotificationObject.objects.filter(recipient=self.admin_user)
        self.assertEqual(admin_notifs.count(), 1)
        notif = admin_notifs.first()
        self.assertEqual(notif.notification_type, 'GROUP_REQUEST')
        self.assertIn('Alpha Innovators', notif.title)
        self.assertIn('applicant_jane', notif.title)
        self.assertNotIn(str(self.group.id), notif.title)

        # 3. Verify actions generated in db
        actions = NotificationAction.objects.filter(notification=notif).order_by('order')
        action_types = [a.action_type for a in actions]
        self.assertIn('APPROVE', action_types)
        self.assertIn('REJECT', action_types)

        # 4. Render payload via adapter
        payload = self.adapter.to_standard_payload(notif)
        self.assertEqual(payload.type, 'GROUP_REQUEST')
        self.assertEqual(payload.context.name, 'Alpha Innovators')
        rendered_action_ids = [a.id for a in payload.actions]
        self.assertIn('APPROVE', rendered_action_ids)
        self.assertIn('REJECT', rendered_action_ids)

    def test_join_approval_notification_wiring_and_actions(self):
        """
        Verify join approval creates GROUP_APPROVED for approved user only,
        has View Group action, clean message with group name (not ID), and zero admin notifications.
        """
        send_group_approved_notification(self.applicant_user, self.group, self.admin_user)

        # 1. Admin gets zero notifications
        admin_notifs = NotificationObject.objects.filter(recipient=self.admin_user)
        self.assertEqual(admin_notifs.count(), 0)

        # 2. Applicant gets exactly one notification
        applicant_notifs = NotificationObject.objects.filter(recipient=self.applicant_user)
        self.assertEqual(applicant_notifs.count(), 1)
        notif = applicant_notifs.first()
        self.assertEqual(notif.notification_type, 'GROUP_APPROVED')
        self.assertIn('Alpha Innovators', notif.title)
        self.assertNotIn(str(self.group.id), notif.title)

        # 3. Actions in database
        actions = NotificationAction.objects.filter(notification=notif)
        self.assertEqual(actions.count(), 1)
        self.assertEqual(actions.first().action_type, 'VIEW_GROUP')
        self.assertEqual(actions.first().label, 'View Group')

        # 4. Render payload
        payload = self.adapter.to_standard_payload(notif)
        self.assertEqual(payload.type, 'GROUP_APPROVED')
        self.assertEqual(payload.context.name, 'Alpha Innovators')
        self.assertEqual(len(payload.actions), 1)
        self.assertEqual(payload.actions[0].id, 'VIEW_GROUP')

    def test_join_rejection_notification_wiring_and_no_action_bar(self):
        """
        Verify join rejection creates GROUP_REJECTED for applicant only,
        has NO action bar, clean message, and zero admin notifications.
        """
        send_group_rejected_notification(self.applicant_user, self.group, self.admin_user)

        # 1. Admin gets zero notifications
        admin_notifs = NotificationObject.objects.filter(recipient=self.admin_user)
        self.assertEqual(admin_notifs.count(), 0)

        # 2. Applicant gets exactly one GROUP_REJECTED notification
        applicant_notifs = NotificationObject.objects.filter(recipient=self.applicant_user)
        self.assertEqual(applicant_notifs.count(), 1)
        notif = applicant_notifs.first()
        self.assertEqual(notif.notification_type, 'GROUP_REJECTED')
        self.assertIn('Alpha Innovators', notif.title)

        # 3. Actions: none created
        actions = NotificationAction.objects.filter(notification=notif)
        self.assertEqual(actions.count(), 0)

        # 4. Profile visibility check
        profile = profile_registry.get_profile('GROUP_REJECTED')
        self.assertFalse(profile.component_visibility.action_bar)

        # 5. Render payload
        payload = self.adapter.to_standard_payload(notif)
        self.assertEqual(payload.type, 'GROUP_REJECTED')
        self.assertEqual(len(payload.actions), 0)

    def test_invitation_notification_wiring_and_actions(self):
        """
        Verify group invitation creates INVITE notification for invitee,
        with Accept and Decline actions.
        """
        send_group_invite_notification(self.applicant_user, self.admin_user, self.group)

        # 1. Admin gets zero notifications
        admin_notifs = NotificationObject.objects.filter(recipient=self.admin_user)
        self.assertEqual(admin_notifs.count(), 0)

        # 2. Applicant gets exactly one INVITE notification
        applicant_notifs = NotificationObject.objects.filter(recipient=self.applicant_user)
        self.assertEqual(applicant_notifs.count(), 1)
        notif = applicant_notifs.first()
        self.assertEqual(notif.notification_type, 'INVITE')

        # 3. Actions in database
        actions = NotificationAction.objects.filter(notification=notif).order_by('order')
        action_types = [a.action_type for a in actions]
        self.assertIn('ACCEPT', action_types)
        self.assertIn('DECLINE', action_types)

        # 4. Render payload
        payload = self.adapter.to_standard_payload(notif)
        self.assertEqual(payload.type, 'INVITE')
        rendered_action_ids = [a.id for a in payload.actions]
        self.assertIn('ACCEPT', rendered_action_ids)
        self.assertIn('DECLINE', rendered_action_ids)

    def test_welcome_open_group_notification_no_raw_ids(self):
        """
        Verify welcome notification uses group name and never numeric ID.
        """
        send_group_welcome_notification(self.applicant_user, self.group)

        notif = NotificationObject.objects.filter(recipient=self.applicant_user).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.notification_type, 'GROUP_APPROVED')
        self.assertIn('Alpha Innovators', notif.title)
        self.assertNotIn(f"added you to {self.group.id}", notif.title)

        payload = self.adapter.to_standard_payload(notif)
        self.assertEqual(payload.context.name, 'Alpha Innovators')

    def test_group_announcement_notification_wiring_and_actions(self):
        """
        Verify group announcement creates GROUP_ANNOUNCEMENT for members (excluding author),
        with Read Announcement action.
        """
        # Add member_user to group
        m = Membership(
            group=self.group,
            user=self.member_user,
            role=MembershipRole.MEMBER,
            status=MembershipStatus.APPROVED
        )
        m._skip_signal_notification = True
        m.save()

        publish_event(
            event_type='groups.announcement.created',
            source=EventSources.GROUPS.value,
            action=EventActions.CREATED.value,
            actor=self.admin_user,
            target_type='Announcement',
            target_id='1',
            context_type='GROUP',
            context_id=str(self.group.id),
            metadata={
                'group_id': self.group.id,
                'group_name': self.group.name,
                'announcement_id': 1,
                'announcement_title': 'Townhall meeting Friday',
            }
        )

        # Admin author gets zero notifications
        admin_notifs = NotificationObject.objects.filter(recipient=self.admin_user)
        self.assertEqual(admin_notifs.count(), 0)

        # Member gets GROUP_ANNOUNCEMENT notification
        member_notifs = NotificationObject.objects.filter(recipient=self.member_user)
        self.assertEqual(member_notifs.count(), 1)
        notif = member_notifs.first()
        self.assertEqual(notif.notification_type, 'GROUP_ANNOUNCEMENT')
        self.assertIn('Alpha Innovators', notif.title)

        # Actions
        actions = NotificationAction.objects.filter(notification=notif)
        self.assertEqual(actions.count(), 1)
        self.assertEqual(actions.first().action_type, 'VIEW_ANNOUNCEMENT')
        self.assertEqual(actions.first().label, 'Read Announcement')

        payload = self.adapter.to_standard_payload(notif)
        self.assertEqual(payload.type, 'GROUP_ANNOUNCEMENT')
        self.assertEqual(len(payload.actions), 1)
        self.assertEqual(payload.actions[0].id, 'VIEW_ANNOUNCEMENT')
