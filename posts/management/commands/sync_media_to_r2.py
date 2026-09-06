"""
Django management command to sync local media files to Cloudflare R2 object storage.

Usage examples:
    # Sync profile pics and group images first (fast):
    python manage.py sync_media_to_r2 --folders profile_pic,group_profile_pic,group_covers,covers

    # Sync all media files in media/:
    python manage.py sync_media_to_r2 --all

    # Dry run to see what would be uploaded:
    python manage.py sync_media_to_r2 --dry-run
"""
import os
import mimetypes
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.core.management.base import BaseCommand
from django.conf import settings
import boto3

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Uploads local media files (profile pics, group images, etc.) to Cloudflare R2 bucket.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--folders',
            type=str,
            default='profile_pic,group_profile_pic,group_covers,covers,thumbnails,previews,documents,announcements,release_images',
            help='Comma-separated list of media subdirectories to sync (default: common media folders).'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Sync the entire media directory (including posts, documents, message attachments).'
        )
        parser.add_argument(
            '--workers',
            type=int,
            default=12,
            help='Number of concurrent worker threads (default: 12).'
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Re-upload and overwrite files even if they already exist in R2.'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show which files would be uploaded without transferring any data.'
        )

    def handle(self, *args, **options):
        media_root = str(settings.MEDIA_ROOT)
        if not os.path.exists(media_root):
            self.stderr.write(self.style.ERROR(f'Media root does not exist: {media_root}'))
            return

        # Load S3 credentials
        endpoint = getattr(settings, 'AWS_S3_ENDPOINT_URL', None) or os.environ.get('AWS_S3_ENDPOINT_URL')
        access_key = getattr(settings, 'AWS_ACCESS_KEY_ID', None) or os.environ.get('AWS_ACCESS_KEY_ID')
        secret_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None) or os.environ.get('AWS_SECRET_ACCESS_KEY')
        bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None) or os.environ.get('AWS_STORAGE_BUCKET_NAME')
        region_name = getattr(settings, 'AWS_S3_REGION_NAME', 'auto')

        if not (endpoint and access_key and secret_key and bucket_name):
            self.stderr.write(self.style.ERROR(
                'Missing Cloudflare R2 credentials in settings or environment. '
                'Ensure AWS_S3_ENDPOINT_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_STORAGE_BUCKET_NAME are set.'
            ))
            return

        s3 = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region_name,
        )

        # Collect local files
        sync_all = options['all']
        folders = [f.strip() for f in options['folders'].split(',') if f.strip()]
        overwrite = options['overwrite']
        dry_run = options['dry_run']
        workers = options['workers']

        files_to_upload = []

        if sync_all:
            search_dirs = [media_root]
        else:
            search_dirs = [os.path.join(media_root, f) for f in folders]

        for target_dir in search_dirs:
            if not os.path.exists(target_dir):
                self.stdout.write(self.style.WARNING(f'Directory does not exist, skipping: {target_dir}'))
                continue

            for root, _, files in os.walk(target_dir):
                # Skip temp directory
                if 'temp' in root.split(os.sep):
                    continue
                for fname in files:
                    full_path = os.path.join(root, fname)
                    rel_to_media = os.path.relpath(full_path, media_root)
                    s3_key = f"media/{rel_to_media.replace(os.sep, '/')}"
                    size = os.path.getsize(full_path)
                    files_to_upload.append((full_path, s3_key, size))

        total_count = len(files_to_upload)
        total_bytes = sum(f[2] for f in files_to_upload)
        total_mb = total_bytes / (1024 * 1024)

        self.stdout.write(self.style.SUCCESS(
            f'Found {total_count} files ({total_mb:.2f} MB) to process in {len(search_dirs)} folder(s).'
        ))

        if total_count == 0:
            self.stdout.write('Nothing to upload.')
            return

        if dry_run:
            self.stdout.write(self.style.WARNING('--- DRY RUN MODE (no files will be uploaded) ---'))
            for _, s3_key, size in files_to_upload[:15]:
                self.stdout.write(f'  Would upload: {s3_key} ({size / 1024:.1f} KB)')
            if total_count > 15:
                self.stdout.write(f'  ... and {total_count - 15} more files.')
            return

        # Fetch existing keys in R2 to avoid redundant uploads unless --overwrite
        existing_keys = set()
        if not overwrite:
            self.stdout.write('Checking existing objects in R2 bucket...')
            paginator = s3.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=bucket_name, Prefix='media/'):
                for item in page.get('Contents', []):
                    existing_keys.add(item['Key'])
            self.stdout.write(f'Found {len(existing_keys)} existing objects in R2.')

        # Upload function for worker
        def upload_single(item):
            local_path, s3_key, file_size = item
            if not overwrite and s3_key in existing_keys:
                return ('skipped', s3_key, file_size)

            content_type, _ = mimetypes.guess_type(local_path)
            if not content_type:
                content_type = 'application/octet-stream'

            extra_args = {
                'ContentType': content_type,
                'CacheControl': 'max-age=604800, public',
            }

            try:
                s3.upload_file(local_path, bucket_name, s3_key, ExtraArgs=extra_args)
                return ('uploaded', s3_key, file_size)
            except Exception as e:
                return ('error', s3_key, str(e))

        # Run concurrent upload
        self.stdout.write(f'Uploading with {workers} worker threads...')
        uploaded_count = 0
        skipped_count = 0
        error_count = 0
        uploaded_bytes = 0

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(upload_single, item): item for item in files_to_upload}
            for future in as_completed(futures):
                status, key, detail = future.result()
                if status == 'uploaded':
                    uploaded_count += 1
                    uploaded_bytes += detail
                    if uploaded_count % 25 == 0 or uploaded_count == total_count:
                        self.stdout.write(f'  Progress: {uploaded_count}/{total_count} files uploaded...')
                elif status == 'skipped':
                    skipped_count += 1
                elif status == 'error':
                    error_count += 1
                    self.stderr.write(self.style.ERROR(f'  Error uploading {key}: {detail}'))

        cdn_domain = getattr(settings, 'CDN_DOMAIN', '')
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Sync complete!\n'
            f'  Uploaded: {uploaded_count} files ({uploaded_bytes / (1024 * 1024):.2f} MB)\n'
            f'  Skipped (already in R2): {skipped_count} files\n'
            f'  Errors: {error_count}\n'
            f'  CDN Domain: https://{cdn_domain}/media/'
        ))
