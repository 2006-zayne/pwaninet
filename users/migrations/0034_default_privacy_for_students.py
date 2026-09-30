from django.db import migrations, models


def move_public_settings_to_members(apps, schema_editor):
    User = apps.get_model('users', 'User')
    User.objects.filter(profile_privacy='PUBLIC').update(profile_privacy='AUTHENTICATED')
    User.objects.filter(post_privacy='PUBLIC').update(post_privacy='AUTHENTICATED')


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0033_heroshowcaseset'),
    ]

    operations = [
        migrations.RunPython(move_public_settings_to_members, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='user',
            name='profile_privacy',
            field=models.CharField(
                choices=[('AUTHENTICATED', 'PwaniNet Users'), ('FOLLOWERS', 'Followers Only'), ('PRIVATE', 'Only Me')],
                default='AUTHENTICATED',
                help_text='Who can view profile information',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='user',
            name='post_privacy',
            field=models.CharField(
                choices=[('AUTHENTICATED', 'PwaniNet Users'), ('FOLLOWERS', 'Followers Only'), ('PRIVATE', 'Only Me')],
                default='AUTHENTICATED',
                help_text='Default visibility for new posts',
                max_length=20,
            ),
        ),
    ]
