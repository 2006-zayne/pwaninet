# Generated migration for adding post shared notification types

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0006_alter_notifications_is_read_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notifications',
            name='notification_type',
            field=models.CharField(
                choices=[
                    ('INVITE', 'Group Invite'),
                    ('ALERT', 'General Alert'),
                    ('LIKE', 'Post Like'),
                    ('FOLLOW', 'New Follower'),
                    ('GROUP_REQUEST', 'Group Join Request'),
                    ('GROUP_APPROVED', 'Group Join Approved'),
                    ('GROUP_REJECTED', 'Group Join Rejected'),
                    ('POST_SHARED', 'Post Shared to User'),
                    ('POST_SHARED_TO_GROUP', 'Post Shared to Group')
                ],
                db_index=True,
                default='ALERT',
                max_length=20
            ),
        ),
    ]
