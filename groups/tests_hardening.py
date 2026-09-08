import uuid
import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import patch

from groups.models import (
    Group, Membership, MembershipRole, MembershipStatus, JoinPolicy,
    InvitePermission, GroupJoinRequest, GroupInvitation
)
from courses.models import Course, Year
from notifications.models import NotificationObject
from groups.services.academic_group_service import enroll_user_in_academic_groups
from documents.academic.models import Faculty, School, Department, Programme, AcademicLevel

User = get_user_model()


class HardenedSubsystemsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.course = Course.objects.create(name='Computer Science')
        self.year = Year.objects.create(course=self.course, level=1)

        self.admin_user = User.objects.create_user(
            username='adminuser',
            email='admin@test.com',
            password='password123',
            course=self.course,
            year=self.year
        )
        self.member_user = User.objects.create_user(
            username='memberuser',
            email='member@test.com',
            password='password123',
            course=self.course,
            year=self.year
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@test.com',
            password='password123',
            course=self.course,
            year=self.year
        )

        self.group = Group.objects.create(
            name='Test Squad',
            created_by=self.admin_user,
            join_policy=JoinPolicy.APPROVAL,
            invite_permission=InvitePermission.ALL_MEMBERS
        )
        # Add admin membership
        Membership.objects.create(
            group=self.group,
            user=self.admin_user,
            role=MembershipRole.ADMIN,
            status=MembershipStatus.APPROVED
        )

    def test_respond_to_invite_accept_and_decline(self):
        """Test responding to group invitation using UUID NotificationObject"""
        self.client.force_login(self.other_user)

        # 1. Test Accept
        invitation = GroupInvitation.objects.create(
            group=self.group,
            inviter=self.admin_user,
            invitee=self.other_user,
            status='PENDING',
            expires_at=timezone.now() + datetime.timedelta(days=7)
        )
        notif = NotificationObject.objects.create(
            recipient=self.other_user,
            notification_type='INVITE',
            context_type='GROUP',
            context_id=str(self.group.id),
            title='Group Invitation',
            metadata={'group_id': self.group.id}
        )

        url = reverse('groups:respond_to_invite', kwargs={'notif_id': notif.notification_id, 'action': 'accept'})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        invitation.refresh_from_db()
        self.assertEqual(invitation.status, 'ACCEPTED')
        notif.refresh_from_db()
        self.assertEqual(notif.status, 'READ')
        self.assertTrue(
            Membership.objects.filter(
                group=self.group,
                user=self.other_user,
                status=MembershipStatus.APPROVED
            ).exists()
        )

        # Clean up membership for decline test
        Membership.objects.filter(group=self.group, user=self.other_user).delete()

        # 2. Test Decline
        invitation2 = GroupInvitation.objects.create(
            group=self.group,
            inviter=self.admin_user,
            invitee=self.other_user,
            status='PENDING',
            expires_at=timezone.now() + datetime.timedelta(days=7)
        )
        Membership.objects.create(
            group=self.group,
            user=self.other_user,
            status=MembershipStatus.PENDING
        )
        notif2 = NotificationObject.objects.create(
            recipient=self.other_user,
            notification_type='INVITE',
            context_type='GROUP',
            context_id=str(self.group.id),
            title='Group Invitation',
            metadata={'group_id': self.group.id}
        )

        url_decline = reverse('groups:respond_to_invite', kwargs={'notif_id': notif2.notification_id, 'action': 'decline'})
        response = self.client.post(url_decline)
        self.assertEqual(response.status_code, 302)

        invitation2.refresh_from_db()
        self.assertEqual(invitation2.status, 'DECLINED')
        notif2.refresh_from_db()
        self.assertEqual(notif2.status, 'READ')
        self.assertFalse(
            Membership.objects.filter(group=self.group, user=self.other_user).exists()
        )

    def test_respond_to_invite_expired(self):
        """Test that responding to an expired invite rejects with EXPIRED status"""
        self.client.force_login(self.other_user)

        invitation = GroupInvitation.objects.create(
            group=self.group,
            inviter=self.admin_user,
            invitee=self.other_user,
            status='PENDING',
            expires_at=timezone.now() - datetime.timedelta(days=1)
        )
        notif = NotificationObject.objects.create(
            recipient=self.other_user,
            notification_type='INVITE',
            context_type='GROUP',
            context_id=str(self.group.id),
            title='Group Invitation',
            metadata={'group_id': self.group.id}
        )

        url = reverse('groups:respond_to_invite', kwargs={'notif_id': notif.notification_id, 'action': 'accept'})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        invitation.refresh_from_db()
        self.assertEqual(invitation.status, 'EXPIRED')
        notif.refresh_from_db()
        self.assertEqual(notif.status, 'EXPIRED')
        self.assertFalse(
            Membership.objects.filter(
                group=self.group,
                user=self.other_user,
                status=MembershipStatus.APPROVED
            ).exists()
        )

    @patch('groups.views.evict_group_member_socket')
    def test_sole_admin_cannot_leave_group(self, mock_evict):
        """Test that the sole administrator cannot leave the group without assigning a successor"""
        self.client.force_login(self.admin_user)
        url = reverse('groups:toggle_membership', kwargs={'group_id': self.group.id})

        response = self.client.post(url)
        # Should stay as member and error message added
        self.assertTrue(
            Membership.objects.filter(
                group=self.group,
                user=self.admin_user,
                role=MembershipRole.ADMIN,
                status=MembershipStatus.APPROVED
            ).exists()
        )
        mock_evict.assert_not_called()

    @patch('groups.views.evict_group_member_socket')
    def test_regular_member_can_leave_and_triggers_socket_eviction(self, mock_evict):
        """Test regular member leaving succeeds and emits socket eviction"""
        mem = Membership.objects.create(
            group=self.group,
            user=self.member_user,
            role=MembershipRole.MEMBER,
            status=MembershipStatus.APPROVED
        )
        self.client.force_login(self.member_user)
        url = reverse('groups:toggle_membership', kwargs={'group_id': self.group.id})

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Membership.objects.filter(group=self.group, user=self.member_user).exists()
        )
        mock_evict.assert_called_once_with(self.group.id, self.member_user.id, reason="You left the group.")

    def test_toggle_membership_approval_policy_creates_join_request(self):
        """Test that requesting to join an approval group creates GroupJoinRequest"""
        self.client.force_login(self.other_user)
        url = reverse('groups:toggle_membership', kwargs={'group_id': self.group.id})

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        join_req = GroupJoinRequest.objects.filter(group=self.group, user=self.other_user).first()
        self.assertIsNotNone(join_req)
        self.assertEqual(join_req.status, 'PENDING')

        # Calling again should not crash (idempotency check)
        response2 = self.client.post(url)
        self.assertEqual(response2.status_code, 302)
        self.assertEqual(GroupJoinRequest.objects.filter(group=self.group, user=self.other_user).count(), 1)

    def test_approve_and_reject_from_notification(self):
        """Test approve_from_notification and peer notification archival"""
        # Create a second admin to test peer notification archival
        admin2 = User.objects.create_user(
            username='admin2', email='admin2@test.com', password='password123'
        )
        Membership.objects.create(
            group=self.group,
            user=admin2,
            role=MembershipRole.ADMIN,
            status=MembershipStatus.APPROVED
        )

        join_req = GroupJoinRequest.objects.create(
            group=self.group,
            user=self.other_user,
            status='PENDING'
        )
        Membership.objects.create(
            group=self.group,
            user=self.other_user,
            status=MembershipStatus.PENDING
        )

        # Create notifications for both admins
        notif1 = NotificationObject.objects.create(
            recipient=self.admin_user,
            notification_type='GROUP',
            context_type='GROUP',
            context_id=str(self.group.id),
            title='Join request',
            metadata={'group_id': self.group.id, 'user_id': self.other_user.id}
        )
        notif2 = NotificationObject.objects.create(
            recipient=admin2,
            notification_type='GROUP',
            context_type='GROUP',
            context_id=str(self.group.id),
            title='Join request',
            metadata={'group_id': self.group.id, 'user_id': self.other_user.id}
        )

        # Admin 1 approves the request
        self.client.force_login(self.admin_user)
        approve_url = reverse(
            'groups:approve_from_notification',
            kwargs={'group_id': self.group.id, 'user_id': self.other_user.id}
        )
        response = self.client.post(approve_url)
        self.assertEqual(response.status_code, 302)

        join_req.refresh_from_db()
        self.assertEqual(join_req.status, 'APPROVED')
        self.assertEqual(join_req.reviewed_by, self.admin_user)

        mem = Membership.objects.get(group=self.group, user=self.other_user)
        self.assertEqual(mem.status, MembershipStatus.APPROVED)

        # Both admins' notifications should be archived
        notif1.refresh_from_db()
        notif2.refresh_from_db()
        self.assertEqual(notif1.status, 'ARCHIVED')
        self.assertEqual(notif2.status, 'ARCHIVED')

    def test_max_5_admins_enforcement(self):
        """Test that promoting a member to admin fails if 5 admins already exist"""
        # Create 4 more admins (total 5)
        for i in range(4):
            u = User.objects.create_user(username=f'extra_admin_{i}', password='password123')
            Membership.objects.create(
                group=self.group,
                user=u,
                role=MembershipRole.ADMIN,
                status=MembershipStatus.APPROVED
            )

        self.assertEqual(
            Membership.objects.filter(group=self.group, role=MembershipRole.ADMIN, status=MembershipStatus.APPROVED).count(),
            5
        )

        candidate = User.objects.create_user(username='candidate', password='password123')
        Membership.objects.create(
            group=self.group,
            user=candidate,
            role=MembershipRole.MEMBER,
            status=MembershipStatus.APPROVED
        )

        self.client.force_login(self.admin_user)
        url = reverse('groups:group_settings_members', kwargs={'group_id': self.group.id})
        response = self.client.post(url, {
            'action': 'assign_role',
            'user_id': candidate.id,
            'role': MembershipRole.ADMIN
        })

        cand_mem = Membership.objects.get(group=self.group, user=candidate)
        self.assertEqual(cand_mem.role, MembershipRole.MEMBER)  # Promotion rejected

    def test_academic_group_auto_enrollment(self):
        """Test academic group auto enrollment with modern programme and academic_level"""
        faculty = Faculty.objects.create(code='SCIFAC', name='Faculty of Science', slug='fac-sci')
        school = School.objects.create(name='School of Pure and Applied Sciences', code='SPAS', slug='spas', faculty=faculty)
        dept = Department.objects.create(name='Computer Science', code='CS', slug='cs', school=school)
        prog = Programme.objects.create(
            name='Bachelor of Science in Computer Science',
            code='BSCCS',
            slug='bsc-cs',
            department=dept,
            degree_type='Bachelor',
            duration_years=4
        )
        lvl = AcademicLevel.objects.create(level=2, name='Year 2')

        official_group = Group.objects.create(
            name='BSc Computer Science Year 2',
            programme=prog,
            academic_level=lvl,
            is_official=True,
            auto_join_on_signup=True,
            join_policy=JoinPolicy.OPEN
        )

        student = User.objects.create_user(
            username='academic_student',
            password='password123',
            programme=prog,
            academic_level=lvl
        )

        enroll_user_in_academic_groups(student)

        self.assertTrue(
            Membership.objects.filter(
                group=official_group,
                user=student,
                status=MembershipStatus.APPROVED
            ).exists()
        )

    def test_group_viewset_api_actions(self):
        """Test DRF endpoints: join, approve, reject, assign_role, leave"""
        # 1. Join API
        self.client.force_login(self.other_user)
        join_url = reverse('groups:group_join_api', kwargs={'pk': self.group.id})
        res = self.client.post(join_url)
        self.assertEqual(res.status_code, 201)
        self.assertTrue(GroupJoinRequest.objects.filter(group=self.group, user=self.other_user, status='PENDING').exists())

        # 2. Approve API
        self.client.force_login(self.admin_user)
        approve_url = reverse('groups:group_approve_api', kwargs={'pk': self.group.id, 'user_id': self.other_user.id})
        res = self.client.post(approve_url)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(Membership.objects.filter(group=self.group, user=self.other_user, status=MembershipStatus.APPROVED).exists())

        # 3. Assign Role API
        assign_url = reverse('groups:group_assign_role', kwargs={'pk': self.group.id})
        res = self.client.post(assign_url, data={'user_id': self.other_user.id, 'role': 'MODERATOR'}, content_type='application/json')
        self.assertEqual(res.status_code, 200)
        mem = Membership.objects.get(group=self.group, user=self.other_user)
        self.assertEqual(mem.role, MembershipRole.MODERATOR)

        # 4. Leave API
        self.client.force_login(self.other_user)
        leave_url = reverse('groups:group_leave', kwargs={'pk': self.group.id})
        res = self.client.post(leave_url)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(Membership.objects.filter(group=self.group, user=self.other_user).exists())


