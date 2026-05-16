from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Group, Membership, JoinPolicy, MembershipRole, MembershipStatus
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
