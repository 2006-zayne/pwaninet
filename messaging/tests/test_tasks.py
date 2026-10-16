from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from django.test import SimpleTestCase

from messaging.tasks import process_video_attachment_task


class ProcessVideoAttachmentTaskTests(SimpleTestCase):
    @patch('messaging.models.MessageAttachment.objects')
    def test_missing_source_file_is_marked_failed_without_retry(
        self, attachment_manager
    ):
        attachment = SimpleNamespace(
            file=SimpleNamespace(
                name='message_attachments/2026/10/11/missing.mp4',
                chunks=Mock(
                    side_effect=FileNotFoundError('source object missing')
                ),
            ),
            processing_status='pending',
            processing_error=None,
            celery_task_id=None,
            save=Mock(),
        )
        attachment_manager.select_related.return_value.get.return_value = (
            attachment
        )

        result = process_video_attachment_task.run('attachment-id')

        self.assertIsNone(result)
        self.assertEqual(attachment.processing_status, 'failed')
        self.assertEqual(attachment.processing_error, 'SOURCE_FILE_MISSING')
        self.assertEqual(attachment.save.call_args_list[-1], call(
            update_fields=['processing_status', 'processing_error']
        ))
