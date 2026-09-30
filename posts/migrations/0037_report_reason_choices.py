from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('posts', '0036_post_visibility'),
    ]

    operations = [
        migrations.AlterField(
            model_name='report',
            name='reason',
            field=models.CharField(
                choices=[
                    ('spam', 'Spam'),
                    ('inappropriate', 'Inappropriate content'),
                    ('harassment', 'Harassment or bullying'),
                    ('false_information', 'False information'),
                    ('copyright', 'Copyright or ownership concern'),
                    ('privacy', 'Privacy concern'),
                    ('other', 'Other'),
                ],
                max_length=50,
            ),
        ),
    ]
