"""Enable pg_trgm extension for fuzzy search."""

from django.db import migrations
from django.contrib.postgres.operations import TrigramExtension


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0005_add_advanced_search_fields'),
    ]

    operations = [
        TrigramExtension(),
    ]
