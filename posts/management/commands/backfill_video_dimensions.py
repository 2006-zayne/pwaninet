import os
import json
import logging
import subprocess
from django.conf import settings
from django.core.management.base import BaseCommand
from posts.models import Post

logger = logging.getLogger(__name__)

FFPROBE = getattr(settings, 'FFPROBE_PATH', '/usr/bin/ffprobe')
if not os.path.isfile(FFPROBE):
    # Fallback to PATH lookup
    import shutil
    FFPROBE = shutil.which('ffprobe') or 'ffprobe'


def get_video_dimensions(file_path):
    """
    Probe a video file using ffprobe and return (width, height, duration, rotation).
    Accounts for orientation tags ('rotate' tag or side data 'rotation').
    When rotation is 90° or 270°, width and height are swapped so that the
    effective display orientation is returned.

    Returns:
        tuple: (width: int, height: int, duration: float, rotation: int) or None if probing fails.
    """
    if not file_path or not os.path.exists(file_path):
        return None

    cmd = [
        FFPROBE,
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_streams',
        '-show_format',
        file_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        info = json.loads(result.stdout)
    except Exception as exc:
        logger.warning("ffprobe failed on %s: %s", file_path, exc)
        return None

    video_stream = next(
        (s for s in info.get('streams', []) if s.get('codec_type') == 'video'),
        None
    )
    if not video_stream:
        return None

    try:
        width = int(video_stream.get('width', 0))
        height = int(video_stream.get('height', 0))
    except (ValueError, TypeError):
        return None

    if width <= 0 or height <= 0:
        return None

    # Probe duration (seconds)
    duration = 0.0
    try:
        duration = float(video_stream.get('duration', 0) or info.get('format', {}).get('duration', 0))
    except (ValueError, TypeError):
        duration = 0.0

    # Probe rotation metadata
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

    normalized_rotate = abs(rotate) % 360
    # If video stream is flagged with 90 or 270 degree rotation, effective display dimensions are swapped
    if normalized_rotate in (90, 270):
        width, height = height, width

    return width, height, duration, normalized_rotate


class Command(BaseCommand):
    help = 'Probe existing video posts, extract dimensions & rotation via ffprobe, and backfill video_width and video_height'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-probe video posts even if video_width and video_height are already set',
        )
        parser.add_argument(
            '--post-id',
            type=int,
            help='Backfill a single post by ID',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Maximum number of posts to process (0 = all)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Inspect and log dimensions without committing changes to the database',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        post_id = options.get('post_id')
        limit = options.get('limit', 0)
        dry_run = options.get('dry_run', False)

        if dry_run:
            self.stdout.write(self.style.WARNING("Running in DRY-RUN mode. No changes will be saved to the database."))

        # Filter posts with video
        qs = Post.objects.filter(video__isnull=False).exclude(video='')

        if post_id:
            qs = qs.filter(id=post_id)
            if not qs.exists():
                self.stderr.write(self.style.ERROR(f"Post with ID {post_id} not found or has no video attached."))
                return

        if not force:
            qs = qs.filter(video_width__isnull=True) | qs.filter(video_height__isnull=True)

        total_count = qs.count()
        if limit > 0:
            qs = qs[:limit]
            self.stdout.write(f"Found {total_count} matching posts. Processing up to {limit} posts...")
        else:
            self.stdout.write(f"Found {total_count} matching posts to probe.")

        processed = 0
        updated = 0
        skipped = 0
        failed = 0
        reels_found = 0

        media_root = getattr(settings, 'MEDIA_ROOT', '')

        for post in qs:
            processed += 1
            post_identifier = f"Post #{post.id} (share_id={getattr(post, 'share_id', 'N/A')})"

            # Resolve local file path
            file_path = None
            if post.video:
                try:
                    file_path = post.video.path
                except (AttributeError, NotImplementedError, ValueError):
                    # For remote storages or missing local path attribute
                    file_path = os.path.join(media_root, str(post.video))

            # Fallback to video_preview if primary video is missing
            if (not file_path or not os.path.exists(file_path)) and post.video_preview:
                try:
                    alt_path = post.video_preview.path
                    if os.path.exists(alt_path):
                        file_path = alt_path
                except Exception:
                    alt_path = os.path.join(media_root, str(post.video_preview))
                    if os.path.exists(alt_path):
                        file_path = alt_path

            if not file_path or not os.path.exists(file_path):
                self.stderr.write(self.style.WARNING(f"[{processed}/{total_count}] {post_identifier}: Video file not found on disk at {file_path}. Skipping."))
                skipped += 1
                continue

            dimensions = get_video_dimensions(file_path)
            if not dimensions:
                self.stderr.write(self.style.ERROR(f"[{processed}/{total_count}] {post_identifier}: ffprobe could not extract video dimensions from {file_path}."))
                failed += 1
                continue

            width, height, duration, rotation = dimensions
            is_vertical = height > width
            aspect_ratio_str = "9:16 portrait/reel" if is_vertical else "16:9 landscape"

            if is_vertical:
                reels_found += 1
                orientation_msg = self.style.SUCCESS(f"-> Detected portrait reel ({width}x{height}, rot={rotation}°)")
            else:
                orientation_msg = self.style.NOTICE(f"-> Detected landscape ({width}x{height}, rot={rotation}°)")

            self.stdout.write(f"[{processed}/{total_count}] {post_identifier}: {width}x{height} (duration={duration:.1f}s) {orientation_msg}")

            if not dry_run:
                update_fields = {
                    'video_width': width,
                    'video_height': height,
                }
                if duration and not post.video_duration:
                    update_fields['video_duration'] = int(duration)

                Post.objects.filter(id=post.id).update(**update_fields)
                updated += 1
            else:
                updated += 1

        action_word = "Would update" if dry_run else "Successfully updated"
        summary_color = self.style.SUCCESS if failed == 0 else self.style.WARNING
        self.stdout.write(summary_color(
            f"\n--- Backfill Summary ---\n"
            f"Total Processed: {processed}\n"
            f"{action_word}: {updated}\n"
            f"Portrait Reels Identified: {reels_found}\n"
            f"Skipped (missing file): {skipped}\n"
            f"Failed (probe error): {failed}\n"
        ))
