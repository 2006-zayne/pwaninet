from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ('messaging', '0011_add_pending_message'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='pendingmessage',
            options={'ordering': ['created_at']},
        ),
        migrations.AddField(
            model_name='pendingmessage',
            name='attachment_url',
            field=models.URLField(blank=True, max_length=2048, null=True),
        ),
        migrations.AddField(
            model_name='pendingmessage',
            name='media_metadata',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='pendingmessage',
            name='message_type',
            field=models.CharField(choices=[('text', 'Text'), ('image', 'Image'), ('video', 'Video'), ('audio', 'Audio'), ('document', 'Document')], default='text', max_length=20),
        ),
        migrations.AddField(
            model_name='pendingmessage',
            name='max_retries',
            field=models.IntegerField(default=3),
        ),
        migrations.AddField(
            model_name='pendingmessage',
            name='queued_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='pendingmessage',
            name='sent_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='pendingmessage',
            name='server_message_id',
            field=models.IntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='pendingmessage',
            name='synced_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='pendingmessage',
            name='status',
            field=models.CharField(choices=[('draft', 'Draft'), ('queued', 'Queued'), ('uploading', 'Uploading'), ('sending', 'Sending'), ('sent', 'Sent'), ('delivered', 'Delivered'), ('read', 'Read'), ('failed', 'Failed'), ('retrying', 'Retrying')], default='draft', max_length=20),
        ),
        migrations.AddIndex(
            model_name='pendingmessage',
            index=models.Index(fields=['server_message_id'], name='messaging_p_server_5e2b1a_idx'),
        ),
        migrations.AddIndex(
            model_name='pendingmessage',
            index=models.Index(fields=['status', 'created_at'], name='messaging_p_status_c_8f3c2b_idx'),
        ),
    ]
