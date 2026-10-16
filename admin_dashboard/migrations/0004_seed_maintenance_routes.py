"""Seed the maintenance route cheat-sheet as inactive locks.

Code ships via git, rows do not: each environment has its own DB, so the
dev row never reaches prod. This migration creates one inactive
PageMaintenance row per site section, so in prod (and PWA, where the URL
bar is hidden) the admin only ticks is_active and edits ETA/message.
"""

from django.db import migrations


ROUTES = [
    # (name, path_prefix)
    ("Home feed", "/"),
    ("Posts", "/post/"),
    ("Posts API", "/api/posts/"),
    ("Uploads page", "/uploads/"),
    ("Uploads API", "/api/uploads/"),
    ("Messaging", "/messaging/"),
    ("Groups", "/groups/"),
    ("Notifications", "/notifications/"),
    ("Courses", "/courses/"),
    ("Documents", "/documents/"),
    ("Search", "/search/"),
    ("Users / profiles", "/users/"),
    ("Pwanimate", "/pwanimate/"),
    ("Pwanimate API", "/api/pwanimate/"),
    ("Dashboard", "/dashboard/"),
    ("Releases", "/system/releases/"),
    ("Downloads / APK", "/download/"),
]


def seed_routes(apps, schema_editor):
    PageMaintenance = apps.get_model("admin_dashboard", "PageMaintenance")
    for name, prefix in ROUTES:
        PageMaintenance.objects.get_or_create(
            path_prefix=prefix,
            defaults={"name": name, "is_active": False},
        )


def unseed_routes(apps, schema_editor):
    PageMaintenance = apps.get_model("admin_dashboard", "PageMaintenance")
    PageMaintenance.objects.filter(
        path_prefix__in=[prefix for _, prefix in ROUTES],
        is_active=False,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("admin_dashboard", "0003_pagemaintenance"),
    ]

    operations = [
        migrations.RunPython(seed_routes, unseed_routes),
    ]
