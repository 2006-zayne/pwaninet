"""
Management command to optimize read receipt tracking by aggregating timestamps.
Reduces database size in group chats by storing only last read time per user.

Usage:
    python manage.py optimize_read_receipts --dry-run
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Max
from messaging.models import MessageRead, ConversationMember, Conversation


class Command(BaseCommand):
    help = 'Optimize read receipts by aggregating per-user last read times'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be optimized without making changes',
        )
        parser.add_argument(
            '--conversation-id',
            type=int,
            help='Only optimize specific conversation',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        conversation_id = options.get('conversation_id')

        # Get conversations to process
        conversations = Conversation.objects.all()
        if conversation_id:
            conversations = conversations.filter(id=conversation_id)

        self.stdout.write(f'Processing {conversations.count()} conversations...')

        total_optimized = 0

        for conversation in conversations:
            self.stdout.write(f'\nProcessing conversation {conversation.id}...')

            # Get members with their latest read message
            members = ConversationMember.objects.filter(
                conversation=conversation
            ).select_related('user')

            for member in members:
                # Get latest read timestamp for this user in this conversation
                latest_read = MessageRead.objects.filter(
                    message__conversation=conversation,
                    user=member.user
                ).aggregate(latest=Max('read_at'))['latest']

                if latest_read and not member.last_read_message:
                    # Find the latest message read by this user
                    latest_message = MessageRead.objects.filter(
                        message__conversation=conversation,
                        user=member.user,
                        read_at=latest_read
                    ).select_related('message').first()

                    if latest_message:
                        if not dry_run:
                            member.last_read_message = latest_message.message
                            member.save()
                        total_optimized += 1

                        self.stdout.write(
                            f'  - User {member.user.username}: '
                            f'last_read_message updated'
                        )

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'[DRY RUN] Would optimize {total_optimized} member read states'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Successfully optimized {total_optimized} member read states'
            ))

            # Optionally cleanup old read receipts (optional, can be done periodically)
            self.stdout.write('\nTip: To cleanup old read receipts, run:')
            self.stdout.write('  MessageRead.objects.filter(read_at__lt=<cutoff>).delete()')
