"""
Management command to archive old messages and cleanup database.
Runs periodically to keep database size manageable.

Usage:
    python manage.py archive_old_messages --days 365 --batch-size 1000 --dry-run
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from messaging.models import Message, MessageRead, MessageReaction
from django.db.models import Q


class Command(BaseCommand):
    help = 'Archive and cleanup old messages to prevent database bloat'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=365,
            help='Archive messages older than N days (default: 365)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Process messages in batches (default: 1000)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without deleting',
        )

    def handle(self, *args, **options):
        days = options['days']
        batch_size = options['batch_size']
        dry_run = options['dry_run']

        cutoff_date = timezone.now() - timedelta(days=days)

        self.stdout.write(f'Finding messages older than {days} days ({cutoff_date})...')

        # Get messages to archive
        old_messages = Message.objects.filter(
            created_at__lt=cutoff_date,
            is_deleted=False
        ).values_list('id', flat=True)

        total_messages = old_messages.count()
        self.stdout.write(f'Found {total_messages} messages to archive')

        if total_messages == 0:
            self.stdout.write(self.style.SUCCESS('No messages to archive'))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY RUN] Would delete:'))
            self.stdout.write(f'  - {total_messages} messages')

            # Count related records
            related_reads = MessageRead.objects.filter(
                message_id__in=old_messages
            ).count()
            related_reactions = MessageReaction.objects.filter(
                message_id__in=old_messages
            ).count()

            self.stdout.write(f'  - {related_reads} read receipts')
            self.stdout.write(f'  - {related_reactions} reactions')

            self.stdout.write(self.style.WARNING('[DRY RUN] No changes made'))
            return

        # Process in batches
        processed = 0
        for i in range(0, total_messages, batch_size):
            batch_ids = list(old_messages[i:i + batch_size])

            # Mark as deleted instead of removing (soft delete for audit trail)
            Message.objects.filter(id__in=batch_ids).update(is_deleted=True)

            processed += len(batch_ids)
            self.stdout.write(f'Processed {processed}/{total_messages} messages')

        self.stdout.write(self.style.SUCCESS(f'Successfully archived {processed} messages'))

        # Optional: Cleanup orphaned read receipts and reactions
        self.stdout.write('Cleaning up orphaned read receipts and reactions...')

        # Delete read receipts for deleted messages
        deleted_reads = MessageRead.objects.filter(
            message__is_deleted=True
        ).delete()

        # Delete reactions for deleted messages
        deleted_reactions = MessageReaction.objects.filter(
            message__is_deleted=True
        ).delete()

        self.stdout.write(self.style.SUCCESS(
            f'Cleanup complete: {deleted_reads[0]} read receipts, '
            f'{deleted_reactions[0]} reactions removed'
        ))
