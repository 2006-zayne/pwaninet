import json
import logging
import os
import shutil
import subprocess
import tempfile
from django.conf import settings
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

FFMPEG = getattr(settings, 'FFMPEG_PATH', '/usr/bin/ffmpeg')
FFPROBE = getattr(settings, 'FFPROBE_PATH', '/usr/bin/ffprobe')


def probe_video_metadata(video_file_or_path):
    """
    Fast synchronous probe of video duration and dimensions via ffprobe,
    accounting for smartphone rotation metadata.
    Returns (duration_seconds, width, height).
    """
    tmp_path = None
    try:
        if isinstance(video_file_or_path, str) and os.path.exists(video_file_or_path):
            video_path = video_file_or_path
        elif hasattr(video_file_or_path, 'path') and os.path.exists(video_file_or_path.path):
            video_path = video_file_or_path.path
        else:
            # File is an in-memory/uploaded file without local path
            ext = os.path.splitext(getattr(video_file_or_path, 'name', '') or '.mp4')[1] or '.mp4'
            tmp_fd, tmp_path = tempfile.mkstemp(prefix='probe_', suffix=ext)
            os.close(tmp_fd)
            if hasattr(video_file_or_path, 'open'):
                video_file_or_path.open('rb')
            if hasattr(video_file_or_path, 'seek'):
                video_file_or_path.seek(0)
            with open(tmp_path, 'wb') as dst:
                if hasattr(video_file_or_path, 'chunks'):
                    for chunk in video_file_or_path.chunks():
                        dst.write(chunk)
                else:
                    shutil.copyfileobj(video_file_or_path, dst)
            video_path = tmp_path

        cmd = [
            FFPROBE, '-v', 'quiet', '-print_format', 'json',
            '-show_streams', video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, check=True)
        info = json.loads(result.stdout)
        video_stream = next(
            (s for s in info.get('streams', []) if s.get('codec_type') == 'video'),
            {}
        )
        duration = float(video_stream.get('duration', 0) or info.get('format', {}).get('duration', 0))
        width = int(video_stream.get('width', 0))
        height = int(video_stream.get('height', 0))

        # Check rotation tags and side data
        rotate = 0
        tags = video_stream.get('tags', {}) or {}
        if 'rotate' in tags:
            try:
                rotate = int(tags['rotate'])
            except (ValueError, TypeError):
                pass

        if not rotate:
            side_data_list = video_stream.get('side_data_list', []) or []
            for sd in side_data_list:
                if 'rotation' in sd:
                    try:
                        rotate = int(sd['rotation'])
                        break
                    except (ValueError, TypeError):
                        pass

        rotate = abs(rotate) % 360
        if rotate in (90, 270):
            width, height = height, width

        return duration, width, height
    except Exception as exc:
        logger.warning('[VideoProbe] Probe failed for %s: %s', video_file_or_path, exc)
        return None, None, None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def generate_fast_video_poster(video_file_or_path, target_width=800):
    """
    Extract first video frame as a JPEG poster image synchronously.
    Returns (filename, ContentFile) or (None, None).
    """
    tmp_path = None
    tmp_poster = None
    try:
        if isinstance(video_file_or_path, str) and os.path.exists(video_file_or_path):
            video_path = video_file_or_path
        elif hasattr(video_file_or_path, 'path') and os.path.exists(video_file_or_path.path):
            video_path = video_file_or_path.path
        else:
            ext = os.path.splitext(getattr(video_file_or_path, 'name', '') or '.mp4')[1] or '.mp4'
            tmp_fd, tmp_path = tempfile.mkstemp(prefix='poster_src_', suffix=ext)
            os.close(tmp_fd)
            if hasattr(video_file_or_path, 'open'):
                video_file_or_path.open('rb')
            if hasattr(video_file_or_path, 'seek'):
                video_file_or_path.seek(0)
            with open(tmp_path, 'wb') as dst:
                if hasattr(video_file_or_path, 'chunks'):
                    for chunk in video_file_or_path.chunks():
                        dst.write(chunk)
                else:
                    shutil.copyfileobj(video_file_or_path, dst)
            video_path = tmp_path

        tmp_poster_fd, tmp_poster = tempfile.mkstemp(prefix='poster_out_', suffix='.jpg')
        os.close(tmp_poster_fd)

        cmd = [
            FFMPEG,
            '-ss', '00:00:00.1',
            '-i', video_path,
            '-vframes', '1',
            '-vf', f'scale={target_width}:-1',
            '-y',
            tmp_poster
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        with open(tmp_poster, 'rb') as f:
            content = f.read()

        base_name = getattr(video_file_or_path, 'name', 'video')
        name_no_ext = os.path.splitext(os.path.basename(base_name))[0]
        filename = f"{name_no_ext}_poster.jpg"
        return filename, ContentFile(content)
    except Exception as exc:
        logger.warning('[VideoProbe] Fast poster generation failed for %s: %s', video_file_or_path, exc)
        return None, None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        if tmp_poster and os.path.exists(tmp_poster):
            try:
                os.remove(tmp_poster)
            except OSError:
                pass
