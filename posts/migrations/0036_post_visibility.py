from django.db import migrations, models


def preserve_existing_posts_as_public(apps, schema_editor):
    Post = apps.get_model('posts', 'Post')
    Post.objects.all().update(visibility='PUBLIC')


class Migration(migrations.Migration):
    dependencies = [
        ('posts', '0035_post_link_preview'),
        ('users', '0034_default_privacy_for_students'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='visibility',
            field=models.CharField(
                choices=[('PUBLIC', 'Legacy public post'), ('AUTHENTICATED', 'PwaniNet Users'), ('FOLLOWERS', 'Followers Only'), ('PRIVATE', 'Only Me')],
                db_index=True,
                default='AUTHENTICATED',
                max_length=20,
            ),
        ),
        migrations.RunPython(preserve_existing_posts_as_public, migrations.RunPython.noop),
    ]
