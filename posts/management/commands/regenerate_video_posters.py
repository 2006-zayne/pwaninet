from django.core.management.base import BaseCommand
from posts.models import Post
from posts.tasks import generate_video_poster
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Regenerate video posters for all posts with videos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenerate posters even if they already exist',
        )
        parser.add_argument(
            '--post-id',
            type=int,
            help='Regenerate poster for a specific post ID only',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        post_id = options.get('post_id')

        queryset = Post.objects.filter(video__isnull=False).exclude(video='')

        if post_id:
            queryset = queryset.filter(id=post_id)
            self.stdout.write(f"Regenerating video poster for post {post_id}")
        else:
            self.stdout.write(f"Found {queryset.count()} posts with videos")

        if not force:
            queryset = queryset.filter(video_poster__isnull=True) | queryset.filter(video_poster='')
            self.stdout.write(f"Regenerating posters for {queryset.count()} posts without existing posters")
        else:
            self.stdout.write(f"Regenerating posters for all {queryset.count()} video posts (force mode)")

        count = 0
        for post in queryset:
            try:
                self.stdout.write(f"Processing post {post.id}...")
                generate_video_poster.delay(post.id)
                count += 1
            except Exception as e:
                self.stderr.write(f"Error processing post {post.id}: {e}")

        self.stdout.write(self.style.SUCCESS(f"Successfully queued {count} video poster generation tasks"))
