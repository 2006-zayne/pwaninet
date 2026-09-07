from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model

from documents.models import Document, DocumentVersion, DocumentFile, Category
from documents.academic.models import AcademicUnit, AcademicYear, Faculty, School, Department, Programme, Semester
from users.models import GlobalRole

User = get_user_model()


class DocumentManagementTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(
            username='docowner',
            email='docowner@example.com',
            password='Password123!'
        )
        self.other_user = User.objects.create_user(
            username='otherstudent',
            email='otherstudent@example.com',
            password='Password123!'
        )
        self.president_user = User.objects.create_user(
            username='president1',
            email='president1@example.com',
            password='Password123!',
            global_role=GlobalRole.PRESIDENT
        )
        self.staff_user = User.objects.create_user(
            username='staff1',
            email='staff1@example.com',
            password='Password123!',
            is_staff=True
        )

        self.category = Category.objects.create(
            code='lecture_notes',
            name='Lecture Notes',
            is_active=True
        )
        self.new_category = Category.objects.create(
            code='past_paper',
            name='Past Paper',
            is_active=True
        )

        self.faculty = Faculty.objects.create(code='FSE', name='Faculty of Science')
        self.school = School.objects.create(faculty=self.faculty, code='SCIT', name='School of Computing')
        self.department = Department.objects.create(school=self.school, code='CS', name='Computer Science')
        self.programme = Programme.objects.create(department=self.department, code='BSCS', name='BSc Computer Science', duration_years=4)
        self.academic_unit = AcademicUnit.objects.create(
            code='CSC101',
            name='Introduction to Programming'
        )
        self.academic_year = AcademicYear.objects.create(
            code='2025/2026',
            name='2025/2026',
            start_date='2025-09-01',
            end_date='2026-08-31',
            is_current=True
        )
        self.semester = Semester.objects.create(
            number=1,
            academic_year=self.academic_year,
            start_date='2025-09-01',
            end_date='2026-01-31',
            is_current=True
        )

        self.document = Document.objects.create(
            title='Original Title',
            description='Original Description',
            category=self.category,
            uploaded_by=self.owner,
            status='ready',
            is_available=True,
            visibility='public'
        )
        self.version = DocumentVersion.objects.create(
            document=self.document,
            version_number=1,
            is_latest=True,
            created_by=self.owner,
            change_notes='Initial release'
        )
        self.doc_file = DocumentFile.objects.create(
            document_version=self.version,
            original_filename='original.pdf',
            storage_path='documents/original.pdf',
            mime_type='application/pdf',
            extension='pdf',
            size_bytes=2048,
            uploaded_by=self.owner
        )

    # ==================== EDIT TESTS ====================

    def test_edit_document_by_owner_success(self):
        self.client.force_login(self.owner)
        data = {
            'title': 'Updated Title',
            'description': 'Updated Description',
            'category': self.new_category.id,
            'academic_unit': self.academic_unit.id,
            'visibility': 'private',
            'language': 'sw',
        }
        response = self.client.post(reverse('documents:edit_document', args=[self.document.id]), data)
        self.assertEqual(response.status_code, 302)

        self.document.refresh_from_db()
        self.assertEqual(self.document.title, 'Updated Title')
        self.assertEqual(self.document.description, 'Updated Description')
        self.assertEqual(self.document.category, self.new_category)
        self.assertEqual(self.document.visibility, 'private')
        self.assertEqual(self.document.language, 'sw')

        primary_unit = self.document.academic_units.filter(is_primary=True).first()
        self.assertIsNotNone(primary_unit)
        self.assertEqual(primary_unit.academic_unit, self.academic_unit)

    def test_edit_document_by_unauthorized_user_forbidden(self):
        self.client.force_login(self.other_user)
        data = {
            'title': 'Hacked Title',
        }
        response = self.client.post(reverse('documents:edit_document', args=[self.document.id]), data)
        self.assertEqual(response.status_code, 403)

        self.document.refresh_from_db()
        self.assertEqual(self.document.title, 'Original Title')

    def test_edit_document_by_president_allowed(self):
        self.client.force_login(self.president_user)
        data = {
            'title': 'Presidential Update',
            'category': self.category.id,
        }
        response = self.client.post(reverse('documents:edit_document', args=[self.document.id]), data)
        self.assertEqual(response.status_code, 302)

        self.document.refresh_from_db()
        self.assertEqual(self.document.title, 'Presidential Update')

    # ==================== DELETE (ARCHIVE) TESTS ====================

    def test_delete_document_by_owner_archives(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('documents:delete_document', args=[self.document.id]))
        self.assertEqual(response.status_code, 302)

        self.document.refresh_from_db()
        self.assertEqual(self.document.status, 'archived')

    def test_delete_document_by_other_user_forbidden(self):
        self.client.force_login(self.other_user)
        response = self.client.post(reverse('documents:delete_document', args=[self.document.id]))
        self.assertEqual(response.status_code, 403)

        self.document.refresh_from_db()
        self.assertEqual(self.document.status, 'ready')

    def test_delete_document_by_staff_allowed(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(reverse('documents:delete_document', args=[self.document.id]))
        self.assertEqual(response.status_code, 302)

        self.document.refresh_from_db()
        self.assertEqual(self.document.status, 'archived')

    # ==================== TOGGLE AVAILABILITY TESTS ====================

    def test_toggle_availability_by_owner(self):
        self.client.force_login(self.owner)
        self.assertTrue(self.document.is_available)

        # Toggle to unavailable
        response = self.client.post(reverse('documents:toggle_availability', args=[self.document.id]))
        self.assertEqual(response.status_code, 302)
        self.document.refresh_from_db()
        self.assertFalse(self.document.is_available)

        # Toggle back to available
        response = self.client.post(reverse('documents:toggle_availability', args=[self.document.id]))
        self.assertEqual(response.status_code, 302)
        self.document.refresh_from_db()
        self.assertTrue(self.document.is_available)

    def test_toggle_availability_by_other_user_forbidden(self):
        self.client.force_login(self.other_user)
        response = self.client.post(reverse('documents:toggle_availability', args=[self.document.id]))
        self.assertEqual(response.status_code, 403)

        self.document.refresh_from_db()
        self.assertTrue(self.document.is_available)

    # ==================== NEW VERSION TESTS ====================

    def test_upload_new_version_success(self):
        self.client.force_login(self.owner)
        new_pdf = SimpleUploadedFile("version2.pdf", b"%PDF-1.4 new version content", content_type="application/pdf")

        with patch('documents.tasks.processing.process_document.delay') as mock_process:
            response = self.client.post(
                reverse('documents:new_version', args=[self.document.id]),
                {'file': new_pdf, 'change_notes': 'Added Chapter 2 formulas'}
            )

        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertTrue(json_data['success'])
        self.assertEqual(json_data['version_number'], 2)

        self.document.refresh_from_db()
        self.assertEqual(self.document.status, 'processing')
        self.assertEqual(self.document.versions.count(), 2)

        old_version = self.document.versions.get(version_number=1)
        self.assertFalse(old_version.is_latest)

        new_version = self.document.versions.get(version_number=2)
        self.assertTrue(new_version.is_latest)
        self.assertEqual(new_version.change_notes, 'Added Chapter 2 formulas')
        self.assertEqual(new_version.files.count(), 1)
        self.assertEqual(new_version.files.first().original_filename, 'version2.pdf')

        mock_process.assert_called_once_with(self.document.id)

    def test_upload_new_version_by_unauthorized_user_forbidden(self):
        self.client.force_login(self.other_user)
        new_pdf = SimpleUploadedFile("unauth.pdf", b"%PDF-1.4 content", content_type="application/pdf")

        response = self.client.post(
            reverse('documents:new_version', args=[self.document.id]),
            {'file': new_pdf}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.document.versions.count(), 1)

    # ==================== SELECTOR & CARD BADGE VERIFICATION ====================

    def test_unavailable_document_hidden_from_public_home(self):
        from documents.selectors.document_selectors import DocumentSelector
        self.document.is_available = False
        self.document.save(update_fields=['is_available'])

        home_docs = DocumentSelector.list_documents_for_home(limit=10)
        self.assertNotIn(self.document, home_docs)

        # But in owner's library uploads it should still appear with unavailable badge
        user_docs = DocumentSelector.list_documents_for_user(user_id=self.owner.id, document_type='uploads')
        self.assertIn(self.document, user_docs)

    def test_card_renders_unavailable_badge_and_management_options(self):
        self.client.force_login(self.owner)
        self.document.is_available = False
        self.document.save(update_fields=['is_available'])

        response = self.client.get(reverse('documents:my_library'), HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')

        self.assertIn('doc-unavailable-badge', content)
        self.assertIn('Unavailable', content)
        self.assertIn('doc-card-options', content)
        self.assertIn('Edit Details', content)
        self.assertIn('New Version', content)
        self.assertIn('Make Available', content)
        self.assertIn('Delete Document', content)
