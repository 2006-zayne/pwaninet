from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('admin_dashboard', '0002_userdailyactivity'),
    ]

    operations = [
        migrations.CreateModel(
            name='PageMaintenance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Admin label, e.g. Messaging. Shown as the affected area.', max_length=100, unique=True)),
                ('path_prefix', models.CharField(help_text='Requests starting with this path show the maintenance page, e.g. /messaging/', max_length=255, unique=True)),
                ('is_active', models.BooleanField(db_index=True, default=False)),
                ('headline', models.CharField(default='This section is temporarily unavailable', max_length=255)),
                ('message', models.TextField(default='We are performing scheduled maintenance on this part of Vasto. No data has been affected. Thank you for your patience.')),
                ('eta', models.DateTimeField(blank=True, help_text='Optional estimated return time shown to users.', null=True)),
                ('show_eta', models.BooleanField(default=True, help_text='Display the ETA on the maintenance page (hidden when no ETA is set).')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
    ]
