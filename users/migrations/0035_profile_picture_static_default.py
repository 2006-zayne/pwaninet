import users.storage
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0034_default_privacy_for_students'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='profile_pic',
            field=models.ImageField(
                blank=True,
                default='profile_pic/default_pic1.jpg',
                null=True,
                storage=users.storage.ProfilePictureStorage(),
                upload_to='profile_pic',
            ),
        ),
    ]
