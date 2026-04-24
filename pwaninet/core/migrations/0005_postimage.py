# Generated migration for PostImage model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_alter_post_options_comment'),
    ]

    operations = [
        migrations.CreateModel(
            name='PostImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='posts/images')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='post_images', to='core.post')),
            ],
            options={
                'ordering': ['order'],
            },
        ),
    ]
