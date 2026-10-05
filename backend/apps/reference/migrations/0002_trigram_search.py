"""Enable pg_trgm and add a trigram index on long descriptions for fuzzy search."""

from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations

CREATE_INDEX = """
CREATE INDEX icd10_long_desc_trgm
ON reference_icd10code USING gin (long_desc gin_trgm_ops)
"""
DROP_INDEX = "DROP INDEX IF EXISTS icd10_long_desc_trgm"


class Migration(migrations.Migration):
    dependencies = [("reference", "0001_initial")]

    operations = [
        TrigramExtension(),
        migrations.RunSQL(CREATE_INDEX, reverse_sql=DROP_INDEX),
    ]
