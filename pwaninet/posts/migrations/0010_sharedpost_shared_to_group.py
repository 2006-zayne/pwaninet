# Generated migration for SharedPost model changes

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0001_initial'),
        ('posts', '0009_post_repost_of'),
    ]

    operations = [
        # Make shared_to field nullable
        migrations.AlterField(
            model_name='sharedpost',
            name='shared_to',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='received_shares',
                to=settings.AUTH_USER_MODEL
            ),
        ),
        
        # Add shared_to_group field
        migrations.AddField(
            model_name='sharedpost',
            name='shared_to_group',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='received_shares',
                to='groups.group'
            ),
        ),
        
        # Remove old unique_together
        migrations.AlterUniqueTogether(
            name='sharedpost',
            unique_together=set(),
        ),
        
        # Add new constraints
        migrations.AddConstraint(
            model_name='sharedpost',
            constraint=models.UniqueConstraint(
                fields=['original_post', 'sharer', 'shared_to'],
                condition=models.Q(shared_to__isnull=False),
                name='unique_user_share'
            ),
        ),
        migrations.AddConstraint(
            model_name='sharedpost',
            constraint=models.UniqueConstraint(
                fields=['original_post', 'sharer', 'shared_to_group'],
                condition=models.Q(shared_to_group__isnull=False),
                name='unique_group_share'
            ),
        ),
        migrations.AddConstraint(
            model_name='sharedpost',
            constraint=models.CheckConstraint(
                condition=models.Q(shared_to__isnull=False) | models.Q(shared_to_group__isnull=False),
                name='share_to_user_or_group'
            ),
        ),
    ]
