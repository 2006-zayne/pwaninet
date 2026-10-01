from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('posts', '0038_report_review_state')]

    operations = [
        migrations.AddField(
            model_name='post',
            name='allow_downloads',
            field=models.BooleanField(default=True, help_text='Allow viewers to download this post’s media'),
        ),
    ]
