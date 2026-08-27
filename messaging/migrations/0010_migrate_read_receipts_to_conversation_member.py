from django.db import migrations, models
from django.db.models import Max


def migrate_read_receipts_to_last_read_message(apps, schema_editor):
    """
    Migrate existing MessageRead data to ConversationMember.last_read_message.
    For each user-conversation pair, set last_read_message to the highest message ID
    that was marked as read in MessageRead.
    """
    MessageRead = apps.get_model('messaging', 'MessageRead')
    ConversationMember = apps.get_model('messaging', 'ConversationMember')
    
    # Group MessageRead by user and conversation
    # For each (user, conversation) pair, find the latest message read
    from django.db.models import Max
    
    # Get all unique (user, conversation) pairs from MessageRead
    read_pairs = MessageRead.objects.values('user_id', 'message__conversation_id').annotate(
        latest_message_id=Max('message_id')
    )
    
    for pair in read_pairs:
        user_id = pair['user_id']
        conversation_id = pair['message__conversation_id']
        latest_message_id = pair['latest_message_id']
        
        # Get or create the ConversationMember
        try:
            member = ConversationMember.objects.get(
                user_id=user_id,
                conversation_id=conversation_id
            )
            # Update last_read_message if it's not already set or if this is newer
            if not member.last_read_message_id or member.last_read_message_id < latest_message_id:
                member.last_read_message_id = latest_message_id
                member.save()
        except ConversationMember.DoesNotExist:
            # This shouldn't happen in normal operation, but handle gracefully
            pass


class Migration(migrations.Migration):
    dependencies = [
        ('messaging', '0009_message_status'),
    ]

    operations = [
        # First, migrate existing data
        migrations.RunPython(
            migrate_read_receipts_to_last_read_message,
            migrations.RunPython.noop  # No reverse migration needed
        ),
        # Then remove the MessageRead model
        migrations.DeleteModel(
            name='MessageRead',
        ),
    ]
