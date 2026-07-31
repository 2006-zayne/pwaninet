"""
Tests for document engagement features.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from documents.models import Document, DocumentVersion, DocumentFile
from documents.engagement.models import (
    DocumentView,
    DocumentDownload,
    DocumentBookmark,
    DocumentRating,
    DocumentShare,
    DocumentAnalytics
)
from courses.models import Course

User = get_user_model()


class DocumentRatingModelTest(TestCase):
    """Test DocumentRating model with thumbs up/down system."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.course = Course.objects.create(
            name='Test Course',
            code='TEST101'
        )
        self.document = Document.objects.create(
            title='Test Document',
            description='Test description',
            uploaded_by=self.user,
            academic_unit=self.course
        )
    
    def test_rating_choices(self):
        """Test that rating only accepts 1 or -1."""
        # Valid thumbs up
        rating_up = DocumentRating.objects.create(
            document=self.document,
            user=self.user,
            rating=1
        )
        self.assertEqual(rating_up.rating, 1)
        self.assertEqual(rating_up.get_rating_display(), 'Thumbs Up')
        
        # Valid thumbs down
        rating_up.delete()
        rating_down = DocumentRating.objects.create(
            document=self.document,
            user=self.user,
            rating=-1
        )
        self.assertEqual(rating_down.rating, -1)
        self.assertEqual(rating_down.get_rating_display(), 'Thumbs Down')
    
    def test_unique_constraint(self):
        """Test that user can only have one rating per document."""
        DocumentRating.objects.create(
            document=self.document,
            user=self.user,
            rating=1
        )
        
        # Attempting to create another rating should fail
        with self.assertRaises(Exception):
            DocumentRating.objects.create(
                document=self.document,
                user=self.user,
                rating=-1
            )
    
    def test_rating_update(self):
        """Test that user can update their rating."""
        rating = DocumentRating.objects.create(
            document=self.document,
            user=self.user,
            rating=1
        )
        self.assertEqual(rating.rating, 1)
        
        # Update rating
        rating.rating = -1
        rating.save()
        self.assertEqual(rating.rating, -1)


class DocumentAnalyticsModelTest(TestCase):
    """Test DocumentAnalytics model for cached statistics."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.course = Course.objects.create(
            name='Test Course',
            code='TEST101'
        )
        self.document = Document.objects.create(
            title='Test Document',
            description='Test description',
            uploaded_by=self.user,
            academic_unit=self.course
        )
    
    def test_analytics_creation(self):
        """Test that analytics can be created for a document."""
        analytics = DocumentAnalytics.objects.create(
            document=self.document,
            view_count=100,
            download_count=50,
            bookmark_count=25
        )
        self.assertEqual(analytics.document, self.document)
        self.assertEqual(analytics.view_count, 100)
        self.assertEqual(analytics.download_count, 50)
        self.assertEqual(analytics.bookmark_count, 25)
    
    def test_rating_percentage_calculation(self):
        """Test that rating percentages are calculated correctly."""
        analytics = DocumentAnalytics.objects.create(
            document=self.document,
            rating_count=10,
            positive_rating_count=7,
            negative_rating_count=3
        )
        analytics.update_rating_percentages()
        self.assertEqual(analytics.positive_rating_percentage, 70)
        self.assertEqual(analytics.negative_rating_percentage, 30)
    
    def test_rating_percentage_zero_division(self):
        """Test that percentage calculation handles zero ratings."""
        analytics = DocumentAnalytics.objects.create(
            document=self.document,
            rating_count=0,
            positive_rating_count=0,
            negative_rating_count=0
        )
        analytics.update_rating_percentages()
        self.assertEqual(analytics.positive_rating_percentage, 0)
        self.assertEqual(analytics.negative_rating_percentage, 0)
    
    def test_one_to_one_relationship(self):
        """Test that each document has only one analytics record."""
        analytics1 = DocumentAnalytics.objects.create(
            document=self.document
        )
        
        # Attempting to create another analytics for same document should fail
        with self.assertRaises(Exception):
            DocumentAnalytics.objects.create(
                document=self.document
            )


class BookmarkToggleViewTest(TestCase):
    """Test bookmark toggle HTMX endpoint."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.course = Course.objects.create(
            name='Test Course',
            code='TEST101'
        )
        self.document = Document.objects.create(
            title='Test Document',
            description='Test description',
            uploaded_by=self.user,
            academic_unit=self.course
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_toggle_bookmark_create(self):
        """Test creating a bookmark via HTMX."""
        url = reverse('documents:toggle_bookmark', args=[self.document.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            DocumentBookmark.objects.filter(
                document=self.document,
                user=self.user
            ).exists()
        )
    
    def test_toggle_bookmark_remove(self):
        """Test removing a bookmark via HTMX."""
        # Create bookmark first
        DocumentBookmark.objects.create(
            document=self.document,
            user=self.user
        )
        
        url = reverse('documents:toggle_bookmark', args=[self.document.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            DocumentBookmark.objects.filter(
                document=self.document,
                user=self.user
            ).exists()
        )
    
    def test_toggle_bookmark_requires_auth(self):
        """Test that bookmark toggle requires authentication."""
        self.client.logout()
        url = reverse('documents:toggle_bookmark', args=[self.document.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 302)  # Redirect to login


class RateDocumentViewTest(TestCase):
    """Test document rating HTMX endpoint."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.course = Course.objects.create(
            name='Test Course',
            code='TEST101'
        )
        self.document = Document.objects.create(
            title='Test Document',
            description='Test description',
            uploaded_by=self.user,
            academic_unit=self.course
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_rate_document_thumbs_up(self):
        """Test rating a document with thumbs up."""
        url = reverse('documents:rate_document', args=[self.document.id])
        response = self.client.post(url, {'rating': 1})
        
        self.assertEqual(response.status_code, 200)
        rating = DocumentRating.objects.get(document=self.document, user=self.user)
        self.assertEqual(rating.rating, 1)
    
    def test_rate_document_thumbs_down(self):
        """Test rating a document with thumbs down."""
        url = reverse('documents:rate_document', args=[self.document.id])
        response = self.client.post(url, {'rating': -1})
        
        self.assertEqual(response.status_code, 200)
        rating = DocumentRating.objects.get(document=self.document, user=self.user)
        self.assertEqual(rating.rating, -1)
    
    def test_rate_document_invalid_rating(self):
        """Test that invalid rating values are rejected."""
        url = reverse('documents:rate_document', args=[self.document.id])
        response = self.client.post(url, {'rating': 5})
        
        self.assertEqual(response.status_code, 400)
    
    def test_rate_document_update_existing(self):
        """Test updating an existing rating."""
        # Create initial rating
        DocumentRating.objects.create(
            document=self.document,
            user=self.user,
            rating=1
        )
        
        # Update rating
        url = reverse('documents:rate_document', args=[self.document.id])
        response = self.client.post(url, {'rating': -1})
        
        self.assertEqual(response.status_code, 200)
        rating = DocumentRating.objects.get(document=self.document, user=self.user)
        self.assertEqual(rating.rating, -1)
    
    def test_rate_document_requires_auth(self):
        """Test that rating requires authentication."""
        self.client.logout()
        url = reverse('documents:rate_document', args=[self.document.id])
        response = self.client.post(url, {'rating': 1})
        
        self.assertEqual(response.status_code, 302)  # Redirect to login


class ShareDocumentViewTest(TestCase):
    """Test document sharing HTMX endpoint."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.course = Course.objects.create(
            name='Test Course',
            code='TEST101'
        )
        self.document = Document.objects.create(
            title='Test Document',
            description='Test description',
            uploaded_by=self.user,
            academic_unit=self.course
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_copy_link_share(self):
        """Test sharing by copying link."""
        url = reverse('documents:share_document', args=[self.document.id])
        response = self.client.post(url, {'share_type': 'copy_link'})
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            DocumentShare.objects.filter(
                document=self.document,
                user=self.user,
                platform='copy_link'
            ).exists()
        )
    
    def test_share_requires_auth(self):
        """Test that sharing requires authentication."""
        self.client.logout()
        url = reverse('documents:share_document', args=[self.document.id])
        response = self.client.post(url, {'share_type': 'copy_link'})
        
        self.assertEqual(response.status_code, 302)  # Redirect to login


class DocumentStatsViewTest(TestCase):
    """Test document statistics HTMX endpoint."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.course = Course.objects.create(
            name='Test Course',
            code='TEST101'
        )
        self.document = Document.objects.create(
            title='Test Document',
            description='Test description',
            uploaded_by=self.user,
            academic_unit=self.course
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_stats_returns_analytics(self):
        """Test that stats endpoint returns cached analytics."""
        # Create analytics
        analytics = DocumentAnalytics.objects.create(
            document=self.document,
            view_count=100,
            download_count=50,
            bookmark_count=25,
            rating_count=10,
            positive_rating_count=7,
            negative_rating_count=3
        )
        analytics.update_rating_percentages()
        
        url = reverse('documents:document_stats', args=[self.document.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['view_count'], 100)
        self.assertEqual(data['download_count'], 50)
        self.assertEqual(data['bookmark_count'], 25)
        self.assertEqual(data['positive_rating_percentage'], 70)
        self.assertEqual(data['negative_rating_percentage'], 30)
    
    def test_stats_creates_analytics_if_missing(self):
        """Test that stats endpoint creates analytics if they don't exist."""
        url = reverse('documents:document_stats', args=[self.document.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            DocumentAnalytics.objects.filter(document=self.document).exists()
        )
    
    def test_stats_requires_auth(self):
        """Test that stats endpoint requires authentication."""
        self.client.logout()
        url = reverse('documents:document_stats', args=[self.document.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 302)  # Redirect to login


class EngagementPermissionsTest(TestCase):
    """Test permissions for engagement features."""
    
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        self.course = Course.objects.create(
            name='Test Course',
            code='TEST101'
        )
        self.document = Document.objects.create(
            title='Test Document',
            description='Test description',
            uploaded_by=self.user1,
            academic_unit=self.course
        )
    
    def test_anonymous_user_cannot_bookmark(self):
        """Test that anonymous users cannot bookmark."""
        url = reverse('documents:toggle_bookmark', args=[self.document.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
    
    def test_anonymous_user_cannot_rate(self):
        """Test that anonymous users cannot rate."""
        url = reverse('documents:rate_document', args=[self.document.id])
        response = self.client.post(url, {'rating': 1})
        self.assertEqual(response.status_code, 302)
    
    def test_anonymous_user_cannot_share(self):
        """Test that anonymous users cannot share."""
        url = reverse('documents:share_document', args=[self.document.id])
        response = self.client.post(url, {'share_type': 'copy_link'})
        self.assertEqual(response.status_code, 302)
