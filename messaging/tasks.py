from celery import shared_task
import os
import shutil
import tempfile
import subprocess
import logging
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


def _resolve_ffmpeg():
    return shutil.which('ffmpeg') or '/usr/bin/ffmpeg'


def _probe_duration(path):
    ffprobe = shutil.which('ffprobe')
    if not ffprobe:
        return None
    try:
        res = subprocess.run(
            [ffprobe, '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        if res.returncode == 0:
            return float(res.stdout.decode().strip())
    except Exception:
        pass
    return None


@shared_task(bind=True, time_limit=600, soft_time_limit=540, max_retries=2,
             autoretry_for=(Exception,), retry_backoff=30)
def process_video_attachment_task(self, attachment_id, trim_start=0.0, trim_end=None,
                                  is_muted=False, rotation=0, is_trimmed=False):
    from messaging.models import MessageAttachment
    try:
        attachment = MessageAttachment.objects.select_related('message').get(id=attachment_id)
    except MessageAttachment.DoesNotExist:
        logger.error(f"[VIDEO_TASK] MessageAttachment {attachment_id} not found.")
        return

    if not attachment.file:
        attachment.processing_status = 'failed'
        attachment.processing_error = 'NO_FILE'
        attachment.save(update_fields=['processing_status', 'processing_error'])
        return

    attachment.processing_status = 'processing'
    attachment.celery_task_id = getattr(self.request, 'id', None)
    attachment.save(update_fields=['processing_status', 'celery_task_id'])

    in_temp_path = out_temp_path = None
    try:
        ext = os.path.splitext(attachment.file.name)[1].lower() or '.mp4'
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as in_temp:
            in_temp_path = in_temp.name
            for chunk in attachment.file.chunks():
                in_temp.write(chunk)

        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as out_temp:
            out_temp_path = out_temp.name

        ffmpeg = _resolve_ffmpeg()
        cmd = [ffmpeg, '-y', '-i', in_temp_path, '-map', '0:v:0?', '-map', '0:a?']

        start_val = max(0.0, float(trim_start)) if trim_start else 0.0
        if start_val > 0.05:
            cmd.extend(['-ss', f'{start_val:.3f}'])

        end_val = float(trim_end) if trim_end else 0.0
        duration = (end_val - start_val) if end_val > start_val else None
        if duration:
            cmd.extend(['-t', f'{duration:.3f}'])

        vf_filters = []
        if rotation:
            rot = int(rotation) % 360
            if rot == 90:
                vf_filters.append('transpose=1')
            elif rot == 180:
                vf_filters.append('transpose=2,transpose=2')
            elif rot == 270:
                vf_filters.append('transpose=2')
        if vf_filters:
            cmd.extend(['-vf', ','.join(vf_filters)])

        cmd.extend(['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23'])
        if is_muted:
            cmd.append('-an')
        else:
            cmd.extend(['-c:a', 'aac', '-b:a', '128k'])
        cmd.extend(['-movflags', '+faststart', out_temp_path])

        logger.info(f"[VIDEO_TASK] Running FFmpeg: {' '.join(cmd)}")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=480)

        if res.returncode != 0:
            err = res.stderr.decode('utf-8', errors='ignore')[-800:]
            logger.error(f"[VIDEO_TASK] FFmpeg failed ({res.returncode}): {err}")
            attachment.processing_status = 'failed'
            attachment.processing_error = f'FFMPEG_{res.returncode}'
            attachment.save(update_fields=['processing_status', 'processing_error'])
            return

        probed = _probe_duration(out_temp_path)
        with open(out_temp_path, 'rb') as f:
            processed_data = f.read()

        old_name = attachment.file.name
        out_name = os.path.splitext(os.path.basename(old_name))[0] + '.mp4'
        attachment.file.save(out_name, ContentFile(processed_data), save=False)
        attachment.size = len(processed_data)
        attachment.duration = duration or probed or attachment.duration
        attachment.processing_status = 'ready'
        attachment.processing_error = None
        attachment.save(update_fields=['file', 'size', 'duration', 'processing_status',
                                        'processing_error'])
        # Keep legacy single-attachment URL in sync
        msg = attachment.message
        if msg and msg.attachment and msg.attachments.count() <= 1:
            msg.attachment = attachment.file.name
            msg.save(update_fields=['attachment'])
        # Best-effort cleanup of orphaned original on renamed key
        try:
            from django.core.files.storage import default_storage
            if old_name and old_name != attachment.file.name and default_storage.exists(old_name):
                default_storage.delete(old_name)
        except Exception:
            pass

        # Push realtime update so sender/receiver swap stale URL
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            layer = get_channel_layer()
            if layer and msg:
                try:
                    url = attachment.file.url
                except Exception:
                    url = None
                async_to_sync(layer.group_send)(f"chat_{msg.conversation_id}", {
                    'type': 'video_ready_event',
                    'message_id': msg.id,
                    'attachment_id': attachment.id,
                    'file_url': url,
                    'duration': attachment.duration,
                })
        except Exception as e:
            logger.warning(f"[VIDEO_TASK] video_ready broadcast failed: {e}")
        logger.info(f"[VIDEO_TASK] Successfully processed video attachment {attachment_id}")

    except FileNotFoundError as e:
        logger.error(
            "[VIDEO_TASK] Source file missing for attachment %s: %s",
            attachment_id,
            e,
        )
        try:
            attachment.processing_status = 'failed'
            attachment.processing_error = 'SOURCE_FILE_MISSING'
            attachment.save(update_fields=['processing_status', 'processing_error'])
        except Exception:
            logger.exception(
                "[VIDEO_TASK] Could not persist missing-source status for %s",
                attachment_id,
            )
        return
    except Exception as e:
        logger.error(f"[VIDEO_TASK] Exception during video processing: {e}", exc_info=True)
        try:
            attachment.processing_status = 'failed'
            attachment.processing_error = str(e)[:500]
            attachment.save(update_fields=['processing_status', 'processing_error'])
        except Exception:
            pass
        raise
    finally:
        for p in (in_temp_path, out_temp_path):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
