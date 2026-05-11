from django.core.management.base import BaseCommand
from messaging.ws_middleware import WebSocketConnectionTracker


class Command(BaseCommand):
    help = 'Clear all WebSocket connections for a specific user'

    def add_arguments(self, parser):
        parser.add_argument('user_id', type=int, help='User ID to clear connections for')

    def handle(self, *args, **options):
        user_id = options['user_id']
        cleared = WebSocketConnectionTracker.clear_all_connections(user_id)
        self.stdout.write(
            self.style.SUCCESS(f'Cleared {cleared} connections for user {user_id}')
        )
