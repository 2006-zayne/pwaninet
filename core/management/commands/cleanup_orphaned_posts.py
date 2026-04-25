from django.core.management.base import BaseCommand
from posts.models import Post


class Command(BaseCommand):
    help = 'Delete orphaned posts that reference deleted groups'

    def handle(self, *args, **options):
        orphaned_count = Post.objects.filter(group__isnull=True).count()
        
        if orphaned_count > 0:
            Post.objects.filter(group__isnull=True).delete()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully deleted {orphaned_count} orphaned posts')
            )
        else:
            self.stdout.write(self.style.WARNING('No orphaned posts found'))
