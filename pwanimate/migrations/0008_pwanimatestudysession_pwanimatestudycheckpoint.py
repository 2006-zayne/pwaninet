import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pwanimate", "0007_attachment_processing_chunks"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PwanimateStudySession",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("paused", "Paused"), ("completed", "Completed")],
                        db_index=True,
                        default="active",
                        max_length=20,
                    ),
                ),
                (
                    "learning_objective",
                    models.TextField(blank=True, default="", help_text="Primary learning objective for this study session"),
                ),
                (
                    "current_topic",
                    models.CharField(blank=True, default="", help_text="Current topic or focus question", max_length=255),
                ),
                (
                    "context_state",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Persisted Context Rail state (active/pinned resource descriptors and page positions)",
                    ),
                ),
                ("resume_banner_dismissed_at", models.DateTimeField(blank=True, null=True)),
                ("started_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("last_active_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "conversation",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="study_session",
                        to="pwanimate.pwanimateconversation",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pwanimate_study_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-last_active_at", "-started_at"],
            },
        ),
        migrations.CreateModel(
            name="PwanimateStudyCheckpoint",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("learning_objective", models.TextField(blank=True, default="")),
                ("current_topic", models.CharField(blank=True, default="", max_length=255)),
                (
                    "concepts_explained",
                    models.JSONField(blank=True, default=list, help_text="Concepts explained by the assistant"),
                ),
                (
                    "concepts_demonstrated",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Concepts demonstrated by the student, with supporting user-message references",
                    ),
                ),
                (
                    "inferred_understanding",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Unverified assistant inference about learner understanding, separated from verified mastery",
                    ),
                ),
                (
                    "misconceptions",
                    models.JSONField(blank=True, default=list, help_text="Misconceptions or unresolved questions"),
                ),
                (
                    "key_discoveries",
                    models.JSONField(blank=True, default=list, help_text="Relevant decisions and discoveries"),
                ),
                ("recommended_next_step", models.TextField(blank=True, default="")),
                (
                    "document_state",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Relevant document and page state at the checkpoint boundary",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="checkpoints",
                        to="pwanimate.pwanimatestudysession",
                    ),
                ),
                (
                    "up_to_message",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="study_checkpoints",
                        to="pwanimate.pwanimatemessage",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddField(
            model_name="pwanimatestudysession",
            name="latest_checkpoint",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="pwanimate.pwanimatestudycheckpoint",
            ),
        ),
        migrations.AddIndex(
            model_name="pwanimatestudysession",
            index=models.Index(fields=["user", "status", "-last_active_at"], name="pwan_study_usr_st_act_idx"),
        ),
        migrations.AddConstraint(
            model_name="pwanimatestudysession",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status", "active")),
                fields=("user",),
                name="pwanimate_unique_active_study_session_per_user",
            ),
        ),
        migrations.AddIndex(
            model_name="pwanimatestudycheckpoint",
            index=models.Index(fields=["session", "-created_at"], name="pwan_study_ckpt_sess_idx"),
        ),
        migrations.AddConstraint(
            model_name="pwanimatestudycheckpoint",
            constraint=models.UniqueConstraint(
                condition=models.Q(("up_to_message__isnull", False)),
                fields=("session", "up_to_message"),
                name="pwanimate_unique_study_ckpt_per_msg",
            ),
        ),
    ]
