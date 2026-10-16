import uuid
from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from users.models import User

from . import states
from .models import UploadEvent, UploadRecord


def make_user(username="uploader"):
    return User.objects.create_user(username=username, password="pass12345")


class StateMachineTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.record = UploadRecord.objects.create(
            user=self.user,
            client_upload_id=uuid.uuid4(),
            filename="clip.mp4",
            file_size=100,
            total_bytes=100,
        )

    def test_happy_path_transitions(self):
        for nxt in ["preparing", "uploading", "verifying", "processing", "publishing", "completed"]:
            self.record.transition_to(nxt)
            self.record.save()
        self.assertEqual(self.record.status, states.COMPLETED)

    def test_illegal_transition_rejected(self):
        with self.assertRaises(ValidationError):
            self.record.transition_to(states.COMPLETED)  # queued -> completed
        self.assertEqual(self.record.status, states.QUEUED)

    def test_pause_resume_and_retry_entries(self):
        self.record.transition_to(states.PREPARING)
        self.record.transition_to(states.UPLOADING)
        self.record.transition_to(states.PAUSED)
        self.record.transition_to(states.UPLOADING)  # resume, no restart
        self.record.transition_to(states.VERIFYING)
        self.record.transition_to(states.UPLOADING)  # parts mismatch refill
        self.record.transition_to(states.VERIFYING)
        self.record.transition_to(states.PROCESSING)
        self.record.transition_to(states.FAILED, error_code="TRANSCODE")
        self.record.transition_to(states.PROCESSING)  # processing retry, no re-upload
        self.assertEqual(self.record.error_code, "TRANSCODE")

    def test_terminal_states_locked(self):
        self.record.transition_to(states.CANCELLED)
        with self.assertRaises(ValidationError):
            self.record.transition_to(states.QUEUED)


class CreateRecoverAPITest(TestCase):
    def setUp(self):
        self.user = make_user("api_uploader")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.payload = {
            "client_upload_id": str(uuid.uuid4()),
            "filename": "coastline.jpg",
            "mime_type": "image/jpeg",
            "file_size": 4_200_000,
        }

    def test_create_then_recover_same_record(self):
        first = self.client.post("/api/uploads/", self.payload, format="json")
        self.assertEqual(first.status_code, 201)
        second = self.client.post("/api/uploads/", self.payload, format="json")
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(
            UploadRecord.objects.filter(
                user=self.user, client_upload_id=self.payload["client_upload_id"]
            ).count(),
            1,
        )
        types = list(
            UploadEvent.objects.filter(record_id=first.data["id"])
            .order_by("created_at")
            .values_list("event_type", flat=True)
        )
        self.assertEqual(types, ["created", "recovered"])

    def test_single_put_protocol_for_small_file(self):
        response = self.client.post("/api/uploads/", self.payload, format="json")
        record = UploadRecord.objects.get(id=response.data["id"])
        self.assertEqual(record.session.protocol, "single-put")
        self.assertEqual(record.session.total_parts, 1)
        self.assertIn("media/uploads/staging/", record.session.r2_key)

    def test_multipart_protocol_for_large_file(self):
        payload = dict(self.payload, client_upload_id=str(uuid.uuid4()),
                       filename="reel.mp4", mime_type="video/mp4",
                       file_size=82_000_000)
        response = self.client.post("/api/uploads/", payload, format="json")
        record = UploadRecord.objects.get(id=response.data["id"])
        self.assertEqual(record.session.protocol, "s3-multipart")
        self.assertEqual(record.session.total_parts, 10)  # ceil(82M / 8MiB)

    def test_auth_required(self):
        self.client.force_authenticate(user=None)
        response = self.client.post("/api/uploads/", self.payload, format="json")
        self.assertIn(response.status_code, (401, 403))


def mock_r2():
    client = MagicMock()
    client.create_multipart_upload.return_value = {"UploadId": "mpu-123"}
    client.generate_presigned_url.side_effect = lambda op, Params, ExpiresIn: (
        f"https://r2.test/{op}/{Params.get('PartNumber', 0)}"
    )
    paginator = MagicMock()
    paginator.paginate.return_value = [
        {"Parts": [{"PartNumber": 1, "ETag": '"aaa"'}]}
    ]
    client.get_paginator.return_value = paginator
    return client


@override_settings(USE_S3=True, AWS_STORAGE_BUCKET_NAME="test-bucket")
class AuthorizeCompleteTest(TestCase):
    def setUp(self):
        self.user = make_user("phase2_user")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _create(self, file_size=4_200_000):
        payload = {
            "client_upload_id": str(uuid.uuid4()),
            "filename": "clip.mp4",
            "mime_type": "video/mp4",
            "file_size": file_size,
        }
        response = self.client.post("/api/uploads/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        return response.data["id"]

    def test_authorize_single_put(self):
        upload_id = self._create()
        with patch("uploads.views.r2.get_r2_client", return_value=mock_r2()):
            response = self.client.post(
                f"/api/uploads/{upload_id}/authorize/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["protocol"], "single-put")
        self.assertEqual(len(response.data["parts"]), 1)
        record = UploadRecord.objects.get(id=upload_id)
        self.assertEqual(record.status, "uploading")

    def test_authorize_multipart_lists_upload_id(self):
        upload_id = self._create(file_size=82_000_000)
        with patch("uploads.views.r2.get_r2_client", return_value=mock_r2()):
            response = self.client.post(
                f"/api/uploads/{upload_id}/authorize/",
                {"parts": [1, 2]}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["upload_id"], "mpu-123")
        self.assertEqual(len(response.data["parts"]), 2)

    def test_complete_multipart_idempotent(self):
        upload_id = self._create(file_size=20_000_000)  # 3 parts
        r2mock = mock_r2()
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {"Parts": [
                {"PartNumber": 1, "ETag": '"aaa"'},
                {"PartNumber": 2, "ETag": '"bbb"'},
                {"PartNumber": 3, "ETag": '"ccc"'},
            ]}
        ]
        r2mock.get_paginator.return_value = paginator
        body = {"parts": [
            {"part_number": 1, "etag": "aaa"},
            {"part_number": 2, "etag": "bbb"},
            {"part_number": 3, "etag": "ccc"},
        ], "post": {"content": "hello"}}
        with patch("uploads.views.r2.get_r2_client", return_value=r2mock):
            self.client.post(
                f"/api/uploads/{upload_id}/authorize/", {}, format="json")
            first = self.client.post(
                f"/api/uploads/{upload_id}/complete/", body, format="json")
            self.assertEqual(first.status_code, 201)
            second = self.client.post(
                f"/api/uploads/{upload_id}/complete/", body, format="json")
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["post_id"], second.data["post_id"])
        record = UploadRecord.objects.get(id=upload_id)
        self.assertEqual(record.status, "processing")
        self.assertEqual(record.post.content, "hello")

    def test_complete_mismatch_returns_422_with_verified(self):
        upload_id = self._create(file_size=20_000_000)  # multipart, 3 parts
        with patch("uploads.views.r2.get_r2_client", return_value=mock_r2()):
            self.client.post(
                f"/api/uploads/{upload_id}/authorize/", {}, format="json")
            response = self.client.post(
                f"/api/uploads/{upload_id}/complete/",
                {"parts": [{"part_number": 1, "etag": "WRONG"}]},
                format="json")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "PARTS_MISMATCH")
        self.assertEqual(response.data["verified_parts"], [1])
        record = UploadRecord.objects.get(id=upload_id)
        self.assertEqual(record.status, "uploading")  # refill, not restart

    def test_retry_and_cancel(self):
        upload_id = self._create()
        record = UploadRecord.objects.get(id=upload_id)
        record.transition_to("preparing")
        record.transition_to("uploading")
        record.transition_to("paused")
        record.save()
        response = self.client.post(f"/api/uploads/{upload_id}/retry/", {}, format="json")
        self.assertEqual(response.data["status"], "uploading")
        response = self.client.post(f"/api/uploads/{upload_id}/cancel/", {}, format="json")
        self.assertEqual(response.data["status"], "cancelled")

    def test_r2_unavailable_returns_503(self):
        upload_id = self._create()
        with override_settings(USE_S3=False):
            response = self.client.post(
                f"/api/uploads/{upload_id}/authorize/", {}, format="json")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["error_code"], "R2_NOT_CONFIGURED")


@override_settings(USE_S3=True, AWS_STORAGE_BUCKET_NAME="test-bucket")
class FinalizeReconcileTest(TestCase):
    def setUp(self):
        self.user = make_user("phase6_user")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _processing_record(self):
        from .models import UploadSession
        record = UploadRecord.objects.create(
            user=self.user, client_upload_id=uuid.uuid4(),
            filename="done.mp4", file_size=100, total_bytes=100,
            status="processing",
        )
        UploadSession.objects.create(
            record=record, protocol="single-put",
            r2_key="media/uploads/staging/x/done.mp4", finalized=True,
        )
        return record

    def test_finalize_copies_and_completes(self):
        from .tasks import finalize_upload_media
        record = self._processing_record()
        from posts.models import Post
        record.post = Post.objects.create(author=self.user, content="shell")
        record.save()
        r2mock = MagicMock()
        with patch("uploads.tasks.r2.get_r2_client", return_value=r2mock):
            result = finalize_upload_media(str(record.id))
        self.assertEqual(result, "completed")
        record.refresh_from_db()
        self.assertEqual(record.status, "completed")
        args, kwargs = r2mock.copy_object.call_args
        self.assertIn("media/posts/", kwargs["Key"])
        # Redelivery is a no-op, never a duplicate.
        with patch("uploads.tasks.r2.get_r2_client", return_value=r2mock):
            self.assertEqual(finalize_upload_media(str(record.id)), "already-done")

    def test_reconcile_fails_stalled_upload(self):
        from django.utils import timezone
        from datetime import timedelta
        from .models import UploadSession
        from .tasks import reconcile_stale_uploads
        record = UploadRecord.objects.create(
            user=self.user, client_upload_id=uuid.uuid4(),
            filename="stuck.mp4", file_size=100, total_bytes=100,
            status="uploading",
        )
        UploadSession.objects.create(
            record=record, protocol="s3-multipart",
            r2_key="media/uploads/staging/x/stuck.mp4",
        )
        UploadRecord.objects.filter(id=record.id).update(
            updated_at=timezone.now() - timedelta(hours=3))
        from . import r2 as r2mod
        with patch("uploads.tasks.r2.get_r2_client",
                   side_effect=r2mod.R2Unavailable("test")):
            reconcile_stale_uploads()
        record.refresh_from_db()
        self.assertEqual(record.status, "failed")
        self.assertEqual(record.error_code, "STALLED")

    def test_delete_tombstone_blocks_uuid_reuse(self):
        payload = {
            "client_upload_id": str(uuid.uuid4()),
            "filename": "gone.jpg",
            "file_size": 1000,
        }
        created = self.client.post("/api/uploads/", payload, format="json")
        upload_id = created.data["id"]
        deleted = self.client.delete(f"/api/uploads/{upload_id}/delete/")
        self.assertEqual(deleted.status_code, 204)
        reuse = self.client.post("/api/uploads/", payload, format="json")
        self.assertEqual(reuse.status_code, 410)
        self.assertEqual(reuse.data["error_code"], "UPLOAD_DELETED")


@override_settings(USE_S3=True, AWS_STORAGE_BUCKET_NAME="test-bucket")
class PostGroupTest(TestCase):
    def setUp(self):
        self.user = make_user("group_user")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _complete_single_put(self, group_id):
        payload = {
            "client_upload_id": str(uuid.uuid4()),
            "post_group": str(group_id),
            "filename": "a.jpg",
            "mime_type": "image/jpeg",
            "file_size": 1000,
        }
        created = self.client.post("/api/uploads/", payload, format="json")
        self.assertEqual(created.status_code, 201)
        upload_id = created.data["id"]
        with patch("uploads.views.r2.get_r2_client", return_value=mock_r2()):
            self.client.post(f"/api/uploads/{upload_id}/authorize/", {}, format="json")
            done = self.client.post(
                f"/api/uploads/{upload_id}/complete/",
                {"parts": [], "post": {"content": "group post"}},
                format="json")
        self.assertEqual(done.status_code, 201)
        return done.data["post_id"]

    def test_group_completes_attach_to_one_post(self):
        from .models import UploadPostGroup
        from posts.models import Post
        group_id = uuid.uuid4()
        before = Post.objects.count()
        first = self._complete_single_put(group_id)
        second = self._complete_single_put(group_id)
        self.assertEqual(first, second)
        self.assertEqual(Post.objects.count(), before + 1)
        self.assertEqual(
            UploadPostGroup.objects.filter(
                user=self.user, group_id=group_id).count(), 1)

    def test_size_cap_enforced_at_create(self):
        response = self.client.post("/api/uploads/", {
            "client_upload_id": str(uuid.uuid4()),
            "filename": "huge.jpg",
            "mime_type": "image/jpeg",
            "file_size": 50 * 1024 * 1024,
        }, format="json")
        self.assertEqual(response.status_code, 400)


@override_settings(USE_S3=True, AWS_STORAGE_BUCKET_NAME="test-bucket")
class FinalizeAttachTest(TestCase):
    @classmethod
    def setUpClass(cls):
        import tempfile
        cls._media_tmp = tempfile.TemporaryDirectory()
        super().setUpClass()

    def setUp(self):
        self.user = make_user("attach_user")
        # PostImage writes go to a temp local dir, never to (mocked) R2.
        local = {
            "default": {
                "BACKEND": "django.core.files.storage.FileSystemStorage",
                "OPTIONS": {"location": self._media_tmp.name},
            },
            "staticfiles": {
                "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
            },
        }
        self._storages = override_settings(STORAGES=local, MEDIA_ROOT=self._media_tmp.name)
        self._storages.enable()
        self.addCleanup(self._storages.disable)

    def _record(self, filename="pic.png", mime="image/png", body=None):
        from .models import UploadSession
        record = UploadRecord.objects.create(
            user=self.user, client_upload_id=uuid.uuid4(),
            filename=filename, mime_type=mime, file_size=len(body or b"x"),
            total_bytes=len(body or b"x"), status="processing",
        )
        UploadSession.objects.create(
            record=record, protocol="single-put",
            r2_key="media/uploads/staging/x/" + filename, finalized=True,
        )
        return record

    def test_image_attached_as_post_image(self):
        import io
        from PIL import Image
        from posts.models import Post, PostImage
        from .tasks import finalize_upload_media
        buf = io.BytesIO()
        Image.new("RGB", (10, 10), "red").save(buf, format="PNG")
        body = buf.getvalue()
        record = self._record(body=body)
        post = Post.objects.create(author=self.user, content="img")
        record.post = post
        record.save()
        r2mock = MagicMock()
        r2mock.get_object.return_value = {"Body": MagicMock(read=MagicMock(return_value=body))}
        with patch("uploads.tasks.r2.get_r2_client", return_value=r2mock):
            self.assertEqual(finalize_upload_media(str(record.id)), "completed")
        self.assertEqual(PostImage.objects.filter(post=post).count(), 1)

    def test_signature_mismatch_rejects(self):
        from .tasks import finalize_upload_media
        record = self._record(filename="fake.png", mime="image/png", body=b"not an image at all...........")
        from posts.models import Post
        record.post = Post.objects.create(author=self.user, content="x")
        record.save()
        r2mock = MagicMock()
        r2mock.get_object.return_value = {"Body": MagicMock(read=MagicMock(return_value=b"not an image at all..........."))}
        with patch("uploads.tasks.r2.get_r2_client", return_value=r2mock):
            self.assertEqual(finalize_upload_media(str(record.id)), "rejected")
        record.refresh_from_db()
        self.assertEqual(record.status, "failed")
        self.assertEqual(record.error_code, "MEDIA_REJECTED")
