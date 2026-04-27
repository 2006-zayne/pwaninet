from django.core.management.base import BaseCommand
from users.models import User, GlobalRole


class Command(BaseCommand):
    help = 'Remove president role from all users except the specified one'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Username of the user to keep as president',
        )

    def handle(self, *args, **options):
        keep_username = options.get('username', 'latoya144')

        # Find all presidents
        presidents = User.objects.filter(global_role=GlobalRole.PRESIDENT)

        if not presidents.exists():
            self.stdout.write(self.style.WARNING('No presidents found.'))
            return

        self.stdout.write(f'Found {presidents.count()} president(s).')

        for president in presidents:
            if president.username == keep_username:
                self.stdout.write(
                    self.style.SUCCESS(f'Keeping {president.username} as president.')
                )
            else:
                president.global_role = GlobalRole.NORMAL
                president.save()
                self.stdout.write(
                    self.style.WARNING(f'Removed president role from {president.username}.')
                )

        self.stdout.write(self.style.SUCCESS('President cleanup complete.'))
