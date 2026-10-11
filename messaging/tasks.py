from celery import shared_task
import os
import tempfile
import subprocess
import logging
from django.core.files.base import ContentFile
from messaging.models import MessageAttachment

logger = logging.getLogger(__name__)

@shared_task(bind=True, time_limit=300, soft_time_limit=270)
def process_video_attachment_task(self, attachment_id, trim_start=0.0, trim_end=None, is_muted=False, rotation=0, is_trimmed=False):
    try:
        attachment = MessageAttachment.objects.get(id=attachment_id)
    except MessageAttachment.DoesNotExist:
        logger.error(f"[VIDEO_TASK] MessageAttachment {attachment_id} not found.")
        return

    if not attachment.file:
        return

    in_temp_path = None
    out_temp_path = None

    try:
        ext = os.path.splitext(attachment.file.name)[1].lower() or '.mp4'
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as in_temp:
            in_temp_path = in_temp.name
            for chunk in attachment.file.chunks():
                in_temp.write(chunk)

        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as out_temp:
            out_temp_path = out_temp.name

        cmd = ['/usr/bin/ffmpeg', '-y', '-i', in_temp_path, '-map', '0:v', '-map', '0:a?']

        start_val = max(0.0, float(trim_start)) if trim_start else 0.0
        if start_val > 0.05:
            cmd.extend(['-ss', f'{start_val:.3f}'])

        end_val = float(trim_end) if trim_end else 0.0
        duration = None
        if end_val > start_val:
            duration = end_val - start_val
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

        logger.info(f"[VIDEO_TASK] Running background FFmpeg: {' '.join(cmd)}")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=240)

        if res.returncode != 0:
            logger.error(f"[VIDEO_TASK] FFmpeg failed ({res.returncode}): {res.stderr.decode('utf-8', errors='ignore')[-400:]}")
            return

        with open(out_temp_path, 'rb') as f:
            processed_data = f.read()

        out_name = os.path.splitext(os.path.basename(attachment.file.name))[0] + '.mp4'
        attachment.file.save(out_name, ContentFile(processed_data), save=False)
        attachment.size = len(processed_data)
        if duration:
            attachment.duration = duration
        attachment.save(update_fields=['file', 'size', 'duration'])
        logger.info(f"[VIDEO_TASK] Successfully processed video attachment {attachment_id}")

    except Exception as e:
        logger.error(f"[VIDEO_TASK] Exception during video processing: {e}", exc_info=True)
    finally:
        if in_temp_path and os.path.exists(in_temp_path):
            try: os.remove(in_temp_path)
            except Exception: pass
        if out_temp_path and os.path.exists(out_temp_path):
            try: os.remove(out_temp_path)
            except Exception: pass
