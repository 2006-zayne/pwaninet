"""Tests for document permissions, API lockdown, and upload CSRF enforcement."""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from documents.models import Category, Document
from users.models import GlobalRole

User = get_user_model()


class DocumentPermissionsApiTest(TestCase):
    """Test API permission enforcement on DocumentViewSet."""

    def setUp(self):
        # Create users
        self.uploader = User.objects.create_user(
            username='uploader',
            email='uploader@example.com',
            password='password123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='password123'
        )
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='password123',
            is_staff=True
        )
        self.president_user = User.objects.create_user(
            username='president',
            email='pres@example.com',
            password='password123',
            global_role=GlobalRole.PRESIDENT
        )

        # Create category
        self.category = Category.objects.create(
            code='lecture_notes',
            name='Lecture Notes',
            is_active=True
        )

        # Create sample public ready document
        self.public_doc = Document.objects.create(
            title='Public Ready Document',
            description='A public document',
            category=self.category,
            uploaded_by=self.uploader,
            status='ready',
            visibility='public'
        )

        # Create sample draft document
        self.draft_doc = Document.objects.create(
            title='Draft Document',
            description='A draft document',
            category=self.category,
            uploaded_by=self.uploader,
            status='draft',
            visibility='private'
        )

        self.client = APIClient()

    def test_anonymous_cannot_delete_document(self):
        """Unauthenticated requests cannot delete documents (returns 401 or 403)."""
        response = self.client.delete(f'/documents/api/documents/{self.public_doc.id}/')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
        self.public_doc.refresh_from_db()
        self.assertEqual(self.public_doc.status, 'ready')

    def test_non_owner_cannot_delete_document(self):
        """A regular authenticated user cannot delete someone else's document (returns 403)."""
        self.client.force_authenticate(user=self.other_user)
        response = self.client.delete(f'/documents/api/documents/{self.public_doc.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.public_doc.refresh_from_db()
        self.assertEqual(self.public_doc.status, 'ready')

    def test_uploader_can_soft_delete_own_document(self):
        """The uploader can delete their own document, which soft-deletes to 'archived'."""
        self.client.force_authenticate(user=self.uploader)
        response = self.client.delete(f'/documents/api/documents/{self.public_doc.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.public_doc.refresh_from_db()
        self.assertEqual(self.public_doc.status, 'archived')

    def test_staff_can_soft_delete_any_document(self):
        """A staff user can delete any document (defaults to soft-delete 'archived')."""
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.delete(f'/documents/api/documents/{self.public_doc.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.public_doc.refresh_from_db()
        self.assertEqual(self.public_doc.status, 'archived')

    def test_staff_can_hard_delete_document_with_query_param(self):
        """Staff with hard_delete=true permanently deletes the document instance."""
        self.client.force_authenticate(user=self.staff_user)
        doc_id = self.public_doc.id
        response = self.client.delete(f'/documents/api/documents/{doc_id}/?hard_delete=true')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Document.objects.filter(id=doc_id).exists())

    def test_non_owner_cannot_edit_document(self):
        """A regular user cannot modify another user's document."""
        self.client.force_authenticate(user=self.other_user)
        response = self.client.patch(
            f'/documents/api/documents/{self.public_doc.id}/',
            {'title': 'Tampered Title'}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_uploader_can_edit_own_document(self):
        """Uploader can modify their own document."""
        self.client.force_authenticate(user=self.uploader)
        response = self.client.patch(
            f'/documents/api/documents/{self.public_doc.id}/',
            {'title': 'Updated Title'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.public_doc.refresh_from_db()
        self.assertEqual(self.public_doc.title, 'Updated Title')

    def test_anonymous_cannot_view_draft_document(self):
        """Unauthenticated user cannot view draft/private documents via API."""
        response = self.client.get(f'/documents/api/documents/{self.draft_doc.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_uploader_can_view_own_draft(self):
        """Uploader can view their own draft document."""
        self.client.force_authenticate(user=self.uploader)
        response = self.client.get(f'/documents/api/documents/{self.draft_doc.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_president_can_view_draft(self):
        """Executive student leader (President) can view non-public documents."""
        self.client.force_authenticate(user=self.president_user)
        response = self.client.get(f'/documents/api/documents/{self.draft_doc.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class DocumentUploadCsrfTest(TestCase):
    """Verify CSRF enforcement on the web upload endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='uploader2',
            email='uploader2@example.com',
            password='password123'
        )
        self.client = Client(enforce_csrf_checks=True)

    def test_upload_view_requires_csrf_for_post(self):
        """POST to upload without CSRF token is rejected with 403 Forbidden."""
        self.client.force_login(self.user)
        response = self.client.post('/documents/upload/', {})
        self.assertEqual(response.status_code, 403)
