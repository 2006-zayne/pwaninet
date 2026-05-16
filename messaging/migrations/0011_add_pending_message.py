from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ('messaging', '0010_migrate_read_receipts_to_conversation_member'),
    ]

    operations = [
        migrations.CreateModel(
            name='PendingMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('temp_id', models.CharField(db_index=True, max_length=100, unique=True)),
                ('content', models.TextField(blank=True, null=True)),
                ('encrypted_content', models.TextField(blank=True, null=True)),
                ('is_encrypted', models.BooleanField(default=False)),
                ('reply_to_id', models.IntegerField(blank=True, null=True)),
                ('attachment', models.FileField(blank=True, null=True, upload_to='pending_attachments/%Y/%m/%d/')),
                ('attachment_type', models.CharField(blank=True, max_length=20, null=True)),
                ('link_url', models.URLField(blank=True, max_length=2048, null=True)),
                ('link_title', models.CharField(blank=True, max_length=500, null=True)),
                ('link_description', models.TextField(blank=True, null=True)),
                ('link_image', models.URLField(blank=True, max_length=2048, null=True)),
                ('link_type', models.CharField(blank=True, max_length=50, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('failed', 'Failed'), ('sent', 'Sent')], default='pending', max_length=20)),
                ('retry_count', models.IntegerField(default=0)),
                ('last_error', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pending_messages', to='messaging.conversation')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pending_messages', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['user', 'status'], name='messaging_p_user_id_6c5f5e_idx'),
                    models.Index(fields=['conversation', 'status'], name='messaging_p_convers_8f3a2c_idx'),
                    models.Index(fields=['temp_id'], name='messaging_p_temp_id_4e1b3a_idx'),
                    models.Index(fields=['created_at'], name='messaging_p_created_5d2c1b_idx'),
                ],
            },
        ),
    ]
