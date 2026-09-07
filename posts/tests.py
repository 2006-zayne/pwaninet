from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Post, PostImage, Like, Comment, CommentLike, Report, Repost, HiddenPost, AuthorPreference, SharedPost
from courses.models import Course, Year, Unit
from groups.models import Group

User = get_user_model()


class PostModelTest(TestCase):
    """Test cases for Post model"""
    
    def setUp(self):
        """Set up test data"""
        self.course = Course.objects.create(name='Computer Science')
        self.year = Year.objects.create(course=self.course, level=1)
        self.unit = Unit.objects.create(code='CS101', name='Intro to CS', course=self.course, year=self.year)
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            course=self.course,
            year=self.year,
            password='testpass123'
        )
        self.post = Post.objects.create(
            author=self.user,
            content='Test post content',
            course=self.course,
            unit=self.unit
        )
    
    def test_post_creation(self):
        """Test that a post can be created"""
        self.assertEqual(self.post.content, 'Test post content')
        self.assertEqual(self.post.author, self.user)
        self.assertEqual(self.post.course, self.course)
    
    def test_post_str(self):
        """Test post string representation"""
        self.assertIn('Post by', str(self.post))
    
    def test_like_count(self):
        """Test like count property"""
        self.assertEqual(self.post.like_count, 0)
        Like.objects.create(user=self.user, post=self.post)
        # Clear cached like_count
        if hasattr(self.post, '_like_count'):
            delattr(self.post, '_like_count')
        self.assertEqual(self.post.like_count, 1)
    
    def test_is_liked_by(self):
        """Test is_liked_by method"""
        self.assertFalse(self.post.is_liked_by(self.user))
        Like.objects.create(user=self.user, post=self.post)
        self.assertTrue(self.post.is_liked_by(self.user))


class LikeModelTest(TestCase):
    """Test cases for Like model"""
    
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
        self.post = Post.objects.create(author=self.user, content='Test post', course=self.course)
    
    def test_like_creation(self):
        """Test that a like can be created"""
        like = Like.objects.create(user=self.user, post=self.post)
        self.assertEqual(like.user, self.user)
        self.assertEqual(like.post, self.post)
    
    def test_unique_like(self):
        """Test that duplicate likes are prevented"""
        Like.objects.create(user=self.user, post=self.post)
        
        with self.assertRaises(Exception):
            Like.objects.create(user=self.user, post=self.post)


class CommentModelTest(TestCase):
    """Test cases for Comment model"""
    
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
        self.post = Post.objects.create(author=self.user, content='Test post', course=self.course)
        self.comment = Comment.objects.create(
            post=self.post,
            author=self.user,
            content='Test comment'
        )
    
    def test_comment_creation(self):
        """Test that a comment can be created"""
        self.assertEqual(self.comment.content, 'Test comment')
        self.assertEqual(self.comment.post, self.post)
        self.assertEqual(self.comment.author, self.user)
    
    def test_comment_str(self):
        """Test comment string representation"""
        self.assertIn('Comment by', str(self.comment))
    
    def test_comment_like(self):
        """Test comment like functionality"""
        self.assertFalse(self.comment.is_liked_by(self.user))
        CommentLike.objects.create(user=self.user, comment=self.comment)
        self.assertTrue(self.comment.is_liked_by(self.user))


class ReportModelTest(TestCase):
    """Test cases for Report model"""
    
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
        self.post = Post.objects.create(author=self.user, content='Test post', course=self.course)
    
    def test_report_creation(self):
        """Test that a report can be created"""
        report = Report.objects.create(
            reporter=self.user,
            post=self.post,
            reason='spam',
            description='This is spam content'
        )
        self.assertEqual(report.reporter, self.user)
        self.assertEqual(report.post, self.post)
        self.assertEqual(report.reason, 'spam')
    
    def test_unique_report(self):
        """Test that duplicate reports are prevented"""
        Report.objects.create(reporter=self.user, post=self.post, reason='spam')
        
        with self.assertRaises(Exception):
            Report.objects.create(reporter=self.user, post=self.post, reason='spam')


class SharedPostModelTest(TestCase):
    """Test cases for SharedPost model"""
    
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
        self.post = Post.objects.create(author=self.user1, content='Test post', course=self.course)
        self.group = Group.objects.create(name='Test Group', created_by=self.user1)
    
    def test_share_to_user(self):
        """Test sharing a post to a user"""
        shared = SharedPost.objects.create(
            original_post=self.post,
            sharer=self.user1,
            shared_to=self.user2,
            message='Check this out'
        )
        self.assertEqual(shared.original_post, self.post)
        self.assertEqual(shared.sharer, self.user1)
        self.assertEqual(shared.shared_to, self.user2)
        self.assertEqual(shared.message, 'Check this out')
    
    def test_share_to_group(self):
        """Test sharing a post to a group"""
        shared = SharedPost.objects.create(
            original_post=self.post,
            sharer=self.user1,
            shared_to_group=self.group,
            message='Check this out'
        )
        self.assertEqual(shared.original_post, self.post)
        self.assertEqual(shared.shared_to_group, self.group)


class PostSerializerFilenameTest(TestCase):
    """Test cases for long filenames in PostCreateSerializer"""

    def setUp(self):
        self.course = Course.objects.create(name='Computer Science')
        self.year = Year.objects.create(course=self.course, level=1)
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            course=self.course,
            year=self.year,
            password='testpass123'
        )

    def test_video_filename_108_characters(self):
        """Test that a video filename with 108 characters is accepted"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from posts.serializers import PostCreateSerializer

        filename = "a" * 104 + ".mp4"  # 108 characters
        video = SimpleUploadedFile(filename, b"fake video content", content_type="video/mp4")

        serializer = PostCreateSerializer(
            data={'video': video, 'content': 'Test video post'},
            context={'request': type('Req', (), {'user': self.user})()}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_video_filename_extremely_long_truncated(self):
        """Test that an extremely long filename (>200 chars) is safely truncated and accepted"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from posts.serializers import PostCreateSerializer

        filename = "b" * 250 + ".mp4"  # 254 characters
        video = SimpleUploadedFile(filename, b"fake video content", content_type="video/mp4")

        serializer = PostCreateSerializer(
            data={'video': video, 'content': 'Test video post'},
            context={'request': type('Req', (), {'user': self.user})()}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertLessEqual(len(video.name), 200)

