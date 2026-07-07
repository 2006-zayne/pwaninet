# Generated migration for comment threading support

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0014_post_video_poster_post_video_preview'),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='parent_comment',
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='replies',
                to='posts.comment'
            ),
        ),
        migrations.AddField(
            model_name='comment',
            name='reply_count',
            field=models.IntegerField(default=0),
        ),
        migrations.AddIndex(
            model_name='comment',
            index=models.Index(fields=['post', 'parent_comment'], name='posts_comment_post_parent_idx'),
        ),
        migrations.AddIndex(
            model_name='comment',
            index=models.Index(fields=['parent_comment', 'created_at'], name='posts_comment_parent_created_idx'),
        ),
    ]
