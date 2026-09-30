"""
Management command to reprocess and backfill link previews for existing posts and messages.
"""

import sys
import logging
from django.core.management.base import BaseCommand
from posts.models import Post
from messaging.services.link_preview_service import LinkPreviewService
from users.services.feed_service import invalidate_home_feed_context

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Scan and reprocess link previews for existing posts and messages containing URLs.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Reprocess previews even if already generated/attached.',
        )
        parser.add_argument(
            '--post-id',
            type=str,
            help='Process a single post by ID or UUID share_id.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Maximum number of items to process.',
        )
        parser.add_argument(
            '--async',
            dest='run_async',
            action='store_true',
            help='Queue preview generation tasks to Celery instead of processing synchronously.',
        )
        parser.add_argument(
            '--messages',
            action='store_true',
            help='Also scan and reprocess chat messages with URLs.',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        post_id = options.get('post_id')
        limit = options.get('limit')
        run_async = options.get('run_async', False)
        include_messages = options.get('messages', False)

        self.stdout.write(self.style.MIGRATE_HEADING("=== Link Preview Reprocessing ==="))
        self.stdout.write(f"Mode: {'Async (Celery)' if run_async else 'Synchronous (Direct)'}")
        self.stdout.write(f"Force: {force}")
        if limit:
            self.stdout.write(f"Limit: {limit}")

        # 1. Process Posts
        self._process_posts(post_id=post_id, force=force, run_async=run_async, limit=limit)

        # 2. Process Messages (if requested)
        if include_messages:
            self._process_messages(force=force, run_async=run_async, limit=limit)

    def _process_posts(self, post_id=None, force=False, run_async=False, limit=None):
        self.stdout.write(self.style.MIGRATE_LABEL("\n--- Scanning Posts ---"))
        
        queryset = Post.objects.exclude(content__isnull=True).exclude(content='').order_by('-created_at')

        if post_id:
            if '-' in str(post_id):
                queryset = queryset.filter(share_id=post_id)
            else:
                queryset = queryset.filter(id=post_id)

        total_scanned = 0
        posts_with_links = []

        for post in queryset:
            total_scanned += 1
            urls = LinkPreviewService.extract_urls(post.content or '')
            if urls:
                posts_with_links.append((post, urls))
                if limit and len(posts_with_links) >= limit:
                    break

        self.stdout.write(f"Scanned {total_scanned} posts. Found {len(posts_with_links)} posts containing external links.")

        success_count = 0
        skipped_count = 0
        failed_count = 0

        for post, urls in posts_with_links:
            first_url = urls[0]

            if not force and post.link_preview_id and not post.link_preview.fetch_failed:
                self.stdout.write(
                    self.style.WARNING(f"  [SKIP] Post {post.id} ({post.share_id}) already has preview: {post.link_preview.title[:40]}")
                )
                skipped_count += 1
                continue

            self.stdout.write(f"\n→ Processing Post {post.id} (author: @{post.author.username if post.author else 'unknown'})")
            self.stdout.write(f"   URL: {first_url}")

            if run_async:
                try:
                    from posts.tasks import generate_post_link_preview_task
                    generate_post_link_preview_task.delay(post.id)
                    self.stdout.write(self.style.SUCCESS(f"   ✓ Queued to Celery"))
                    success_count += 1
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"   ✗ Celery queue error: {e}"))
                    failed_count += 1
            else:
                try:
                    preview = LinkPreviewService.generate_preview_for_post(post)
                    if preview:
                        # If post had gradient text style without local media, switch to 'none' so preview card renders clearly
                        if post.gradient_class != 'none' and not post.images.exists() and not post.video and not post.audio and not post.docs and not post.shared_document:
                            post.gradient_class = 'none'
                            post.save(update_fields=['gradient_class'])

                        if post.author_id:
                            invalidate_home_feed_context(post.author_id)

                        self.stdout.write(self.style.SUCCESS(f"   ✓ Preview generated:"))
                        self.stdout.write(f"     Title: {preview.title}")
                        self.stdout.write(f"     Domain: {preview.domain} ({preview.site_name})")
                        self.stdout.write(f"     Media Type: {preview.media_type}")
                        self.stdout.write(f"     Has Thumbnail: {preview.has_thumbnail()} ({preview.thumbnail_url[:60] if preview.thumbnail_url else 'None'})")
                        success_count += 1
                    else:
                        self.stdout.write(self.style.WARNING(f"   - No preview generated for {first_url}"))
                        failed_count += 1
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"   ✗ Error: {e}"))
                    failed_count += 1

        self.stdout.write(self.style.MIGRATE_HEADING("\n--- Post Processing Summary ---"))
        self.stdout.write(self.style.SUCCESS(f"  Successfully processed: {success_count}"))
        self.stdout.write(self.style.WARNING(f"  Skipped (already have preview): {skipped_count}"))
        if failed_count > 0:
            self.stdout.write(self.style.ERROR(f"  Failed / No preview: {failed_count}"))

    def _process_messages(self, force=False, run_async=False, limit=None):
        from messaging.models import Message

        self.stdout.write(self.style.MIGRATE_LABEL("\n--- Scanning Chat Messages ---"))
        queryset = Message.objects.exclude(content__isnull=True).exclude(content='').order_by('-created_at')

        messages_with_links = []
        for msg in queryset:
            urls = LinkPreviewService.extract_urls(msg.content or '')
            if urls:
                messages_with_links.append((msg, urls))
                if limit and len(messages_with_links) >= limit:
                    break

        self.stdout.write(f"Found {len(messages_with_links)} messages with links.")

        msg_success = 0
        msg_skipped = 0
        msg_failed = 0

        for msg, urls in messages_with_links:
            if not force and msg.link_preview_id and not msg.link_preview.fetch_failed:
                msg_skipped += 1
                continue

            try:
                preview = LinkPreviewService.generate_preview_for_message(msg)
                if preview:
                    msg_success += 1
                else:
                    msg_failed += 1
            except Exception as e:
                msg_failed += 1

        self.stdout.write(self.style.MIGRATE_HEADING("\n--- Message Processing Summary ---"))
        self.stdout.write(self.style.SUCCESS(f"  Successfully processed messages: {msg_success}"))
        self.stdout.write(self.style.WARNING(f"  Skipped messages: {msg_skipped}"))
        if msg_failed > 0:
            self.stdout.write(self.style.ERROR(f"  Failed messages: {msg_failed}"))
