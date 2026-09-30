import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pwanimate", "0006_pwanimateattachment"),
    ]

    operations = [
        migrations.AddField(
            model_name="pwanimateattachment",
            name="processing_status",
            field=models.CharField(
                choices=[
                    ("not_required", "Not required"),
                    ("pending", "Pending"),
                    ("processing", "Processing"),
                    ("ready", "Ready"),
                    ("failed", "Failed"),
                ],
                db_index=True,
                default="not_required",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="pwanimateattachment",
            name="processing_error",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="pwanimateattachment",
            name="processed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="PwanimateAttachmentChunk",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("chunk_index", models.PositiveIntegerField()),
                ("content", models.TextField()),
                ("content_hash", models.CharField(db_index=True, max_length=64)),
                ("page_number", models.PositiveIntegerField(blank=True, null=True)),
                ("page_end", models.PositiveIntegerField(blank=True, null=True)),
                ("chunk_type", models.CharField(default="text", max_length=30)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "attachment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chunks",
                        to="pwanimate.pwanimateattachment",
                    ),
                ),
            ],
            options={
                "ordering": ["attachment_id", "chunk_index"],
                "indexes": [models.Index(fields=["attachment", "page_number"], name="pwan_attach_page_idx")],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("attachment", "chunk_index"),
                        name="pwanimate_attachment_chunk_unique",
                    ),
                ],
            },
        ),
    ]
