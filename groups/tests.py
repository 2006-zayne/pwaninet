from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Group, Membership, JoinPolicy, MembershipRole, MembershipStatus, Announcement, AnnouncementPriority
from courses.models import Course, Year

User = get_user_model()


class GroupModelTest(TestCase):
    """Test cases for Group model"""
    
    def setUp(self):
        """Set up test data"""
        self.course = Course.objects.create(name='Computer Science')
        self.year = Year.objects.create(course=self.course, level=1)
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            course=self.course,
            year=self.year,
            password='testpass123'
        )
        self.group = Group.objects.create(
            name='Test Group',
            created_by=self.user,
            description='A test group',
            course=self.course,
            year=self.year
        )
    
    def test_group_creation(self):
        """Test that a group can be created"""
        self.assertEqual(self.group.name, 'Test Group')
        self.assertEqual(self.group.created_by, self.user)
        self.assertEqual(self.group.course, self.course)
    
    def test_group_str(self):
        """Test group string representation"""
        self.assertEqual(str(self.group), 'Test Group')
    
    def test_join_policy_choices(self):
        """Test join policy field choices"""
        self.group.join_policy = JoinPolicy.APPROVAL
        self.group.save()
        self.assertEqual(self.group.join_policy, 'approval')
    
    def test_official_group(self):
        """Test official group designation"""
        self.group.is_official = True
        self.group.save()
        self.assertTrue(self.group.is_official)


class MembershipModelTest(TestCase):
    """Test cases for Membership model"""
    
    def setUp(self):
        """Set up test data"""
        self.course = Course.objects.create(name='Computer Science')
        self.year = Year.objects.create(course=self.course, level=1)
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            course=self.course,
            year=self.year,
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            course=self.course,
            year=self.year,
            password='testpass123'
        )
        self.group = Group.objects.create(name='Test Group', created_by=self.user1, course=self.course)
    
    def test_membership_creation(self):
        """Test that a membership can be created"""
        membership = Membership.objects.create(
            user=self.user2,
            group=self.group,
            role=MembershipRole.MEMBER,
            status=MembershipStatus.APPROVED
        )
        self.assertEqual(membership.user, self.user2)
        self.assertEqual(membership.group, self.group)
        self.assertEqual(membership.role, 'MEMBER')
        self.assertEqual(membership.status, 'APPROVED')
    
    def test_unique_membership(self):
        """Test that duplicate memberships are prevented"""
        Membership.objects.create(
            user=self.user2,
            group=self.group,
            role=MembershipRole.MEMBER,
            status=MembershipStatus.APPROVED
        )
        
        with self.assertRaises(Exception):
            Membership.objects.create(
                user=self.user2,
                group=self.group,
                role=MembershipRole.MEMBER,
                status=MembershipStatus.APPROVED
            )
    
    def test_membership_str(self):
        """Test membership string representation"""
        membership = Membership.objects.create(
            user=self.user2,
            group=self.group,
            role=MembershipRole.MEMBER,
            status=MembershipStatus.APPROVED
        )
        self.assertEqual(str(membership), 'user2 - Test Group (MEMBER)')
        self.assertIn('Test Group', str(membership))
    
    def test_role_choices(self):
        """Test role field choices"""
        membership = Membership.objects.create(
            user=self.user2,
            group=self.group,
            role=MembershipRole.ADMIN,
            status=MembershipStatus.APPROVED
        )
        self.assertEqual(membership.role, 'ADMIN')
    
    def test_status_choices(self):
        """Test status field choices"""
        membership = Membership.objects.create(
            user=self.user2,
            group=self.group,
            role=MembershipRole.MEMBER,
            status=MembershipStatus.PENDING
        )
        self.assertEqual(membership.status, 'PENDING')


class AnnouncementModelTest(TestCase):
    """Test cases for Announcement model"""
    
    def setUp(self):
        """Set up test data"""
        self.course = Course.objects.create(name='Computer Science')
        self.year = Year.objects.create(course=self.course, level=1)
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            course=self.course,
            year=self.year,
            password='testpass123'
        )
        self.group = Group.objects.create(
            name='Test Group',
            created_by=self.user,
            description='A test group',
            course=self.course,
            year=self.year
        )
        self.membership = Membership.objects.create(
            user=self.user,
            group=self.group,
            role=MembershipRole.ADMIN,
            status=MembershipStatus.APPROVED
        )
    
    def test_announcement_creation(self):
        """Test that an announcement can be created"""
        announcement = Announcement.objects.create(
            group=self.group,
            author=self.user,
            title='Test Announcement',
            content='This is a test announcement',
            priority=AnnouncementPriority.NORMAL
        )
        self.assertEqual(announcement.title, 'Test Announcement')
        self.assertEqual(announcement.group, self.group)
        self.assertEqual(announcement.author, self.user)
        self.assertEqual(announcement.priority, 'NORMAL')
        self.assertFalse(announcement.is_pinned)
    
    def test_announcement_str(self):
        """Test announcement string representation"""
        announcement = Announcement.objects.create(
            group=self.group,
            author=self.user,
            title='Test Announcement',
            content='This is a test announcement'
        )
        self.assertEqual(str(announcement), 'Test Announcement - Test Group')
    
    def test_announcement_priority_choices(self):
        """Test priority field choices"""
        announcement = Announcement.objects.create(
            group=self.group,
            author=self.user,
            title='Important Announcement',
            content='This is important',
            priority=AnnouncementPriority.IMPORTANT
        )
        self.assertEqual(announcement.priority, 'IMPORTANT')
        
        announcement.priority = AnnouncementPriority.URGENT
        announcement.save()
        self.assertEqual(announcement.priority, 'URGENT')
    
    def test_announcement_pinned_state(self):
        """Test pinned state"""
        announcement = Announcement.objects.create(
            group=self.group,
            author=self.user,
            title='Pinned Announcement',
            content='This is pinned',
            is_pinned=True
        )
        self.assertTrue(announcement.is_pinned)
        
        announcement.is_pinned = False
        announcement.save()
        self.assertFalse(announcement.is_pinned)
    
    def test_announcement_ordering(self):
        """Test that announcements are ordered correctly (pinned first, then by date)"""
        announcement1 = Announcement.objects.create(
            group=self.group,
            author=self.user,
            title='First Announcement',
            content='First',
            is_pinned=False
        )
        announcement2 = Announcement.objects.create(
            group=self.group,
            author=self.user,
            title='Pinned Announcement',
            content='Pinned',
            is_pinned=True
        )
        announcement3 = Announcement.objects.create(
            group=self.group,
            author=self.user,
            title='Second Announcement',
            content='Second',
            is_pinned=False
        )
        
        announcements = list(Announcement.objects.filter(group=self.group))
        # Pinned should come first
        self.assertEqual(announcements[0].is_pinned, True)
        self.assertEqual(announcements[0].title, 'Pinned Announcement')
        # Non-pinned should be ordered by date (newest first)
        self.assertEqual(announcements[1].title, 'Second Announcement')
        self.assertEqual(announcements[2].title, 'First Announcement')
    
    def test_announcement_group_isolation(self):
        """Test that announcements belong to specific groups"""
        group2 = Group.objects.create(
            name='Test Group 2',
            created_by=self.user,
            description='Another test group',
            course=self.course,
            year=self.year
        )
        
        announcement1 = Announcement.objects.create(
            group=self.group,
            author=self.user,
            title='Group 1 Announcement',
            content='For group 1'
        )
        
        announcement2 = Announcement.objects.create(
            group=group2,
            author=self.user,
            title='Group 2 Announcement',
            content='For group 2'
        )
        
        group1_announcements = Announcement.objects.filter(group=self.group)
        group2_announcements = Announcement.objects.filter(group=group2)
        
        self.assertEqual(group1_announcements.count(), 1)
        self.assertEqual(group2_announcements.count(), 1)
        self.assertEqual(group1_announcements.first().title, 'Group 1 Announcement')
        self.assertEqual(group2_announcements.first().title, 'Group 2 Announcement')
    
    def test_announcement_attachment(self):
        """Test announcement attachment field"""
        announcement = Announcement.objects.create(
            group=self.group,
            author=self.user,
            title='Announcement with Attachment',
            content='This has an attachment'
        )
        # Test that attachments relationship exists and can be empty
        self.assertEqual(announcement.attachments.count(), 0)
