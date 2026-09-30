from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('posts', '0037_report_reason_choices'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='status',
            field=models.CharField(choices=[('PENDING', 'Pending'), ('REVIEWED', 'Reviewed'), ('ACTIONED', 'Action taken'), ('DISMISSED', 'Dismissed')], db_index=True, default='PENDING', max_length=16),
        ),
        migrations.AddField(
            model_name='report',
            name='reviewed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='report',
            name='reviewed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_post_reports', to=settings.AUTH_USER_MODEL),
        ),
    ]
