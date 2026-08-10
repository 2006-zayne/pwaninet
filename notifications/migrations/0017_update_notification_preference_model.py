# Generated manually to update NotificationPreference model

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0016_create_delivery_attempt'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Delete old NotificationPreference model
        migrations.DeleteModel(
            name='NotificationPreference',
        ),
        
        # Create new simplified NotificationPreference model
        migrations.CreateModel(
            name='NotificationPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email_enabled', models.BooleanField(default=True, help_text='Enable email notifications')),
                ('email_digest', models.BooleanField(default=False, help_text='Send daily digest instead of immediate emails')),
                ('push_enabled', models.BooleanField(default=True, help_text='Enable push notifications')),
                ('push_sound', models.BooleanField(default=True, help_text='Play sound for push notifications')),
                ('in_app_enabled', models.BooleanField(default=True, help_text='Enable in-app notifications')),
                ('type_preferences', models.JSONField(blank=True, default=dict, help_text='Per-notification-type delivery preferences')),
                ('quiet_hours_enabled', models.BooleanField(default=False, help_text='Enable quiet hours')),
                ('quiet_hours_start', models.TimeField(blank=True, help_text='Quiet hours start time', null=True)),
                ('quiet_hours_end', models.TimeField(blank=True, help_text='Quiet hours end time', null=True)),
                ('max_notifications_per_hour', models.PositiveIntegerField(default=50, help_text='Maximum notifications per hour', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(100)])),
                ('do_not_disturb_until', models.DateTimeField(blank=True, help_text='Do not disturb until this time', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(db_index=True, on_delete=django.db.models.deletion.CASCADE, related_name='notification_preferences', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Notification Preference',
                'verbose_name_plural': 'Notification Preferences',
            },
        ),
    ]
