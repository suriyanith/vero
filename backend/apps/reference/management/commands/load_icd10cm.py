"""Load the ICD-10-CM order file and tabular XML into the reference tables.

Idempotent (rerunning produces the same end state), transactional (all or
nothing), and versioned (rows hang off a CodeSetVersion, which becomes the
single active one).
"""

import hashlib
from datetime import date
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django.db import connection, transaction

from apps.reference.models import CodeSetVersion, Icd10Code
from apps.reference.parsers import compute_parent_codes, parse_order_file, parse_tabular_xml

CMS_ICD10_URL = "https://www.cms.gov/medicare/coding-billing/icd-10-codes"
BATCH_SIZE = 5000

SEARCH_VECTOR_SQL = """
UPDATE reference_icd10code SET search_vector =
  setweight(to_tsvector('english', long_desc), 'A') ||
  setweight(to_tsvector('english', coalesce(
    (SELECT string_agg(term, ' ')
     FROM jsonb_array_elements_text(notes -> 'inclusion_terms') AS term), '')), 'B')
WHERE code_set_id = %s
"""


class Command(BaseCommand):
    help = "Load an ICD-10-CM release (order file + tabular XML)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--fy", type=int, required=True, help="Fiscal year, e.g. 2027")
        parser.add_argument("--order-file", type=Path, required=True)
        parser.add_argument("--tabular-xml", type=Path, required=True)
        parser.add_argument("--source-url", default=CMS_ICD10_URL)

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        fy: int = options["fy"]
        order_rows = parse_order_file(options["order_file"])
        notes_map = parse_tabular_xml(options["tabular_xml"])
        sha256 = hashlib.sha256(options["order_file"].read_bytes()).hexdigest()

        version, _ = CodeSetVersion.objects.update_or_create(
            system="ICD10CM",
            fiscal_year=fy,
            defaults={
                # ICD-10-CM fiscal years start the previous October 1.
                "effective_from": date(fy - 1, 10, 1),
                "source_url": options["source_url"],
                "sha256": sha256,
                "is_active": True,
            },
        )
        CodeSetVersion.objects.filter(system="ICD10CM").exclude(pk=version.pk).update(
            is_active=False
        )
        version.codes.all().delete()

        all_codes = {row.code for row in order_rows}
        parents = compute_parent_codes(all_codes)

        def notes_for(code: str) -> dict[str, list[str]]:
            # Exact XML entry, or the nearest ancestor's notes: 7th-character
            # codes exist only in the order file, not as XML <diag> nodes.
            for length in range(len(code), 2, -1):
                if code[:length] in notes_map:
                    return notes_map[code[:length]]
            return {}

        objects = [
            Icd10Code(
                code_set=version,
                code=row.code,
                display_code=(f"{row.code[:3]}.{row.code[3:]}" if len(row.code) > 3 else row.code),
                short_desc=row.short_desc,
                long_desc=row.long_desc,
                is_billable=row.is_billable,
                category=row.code[:3],
                parent_code=parents[row.code],
                notes=notes_for(row.code),
            )
            for row in order_rows
        ]
        Icd10Code.objects.bulk_create(objects, batch_size=BATCH_SIZE)

        with connection.cursor() as cursor:
            cursor.execute(SEARCH_VECTOR_SQL, [version.pk])

        billable = sum(1 for row in order_rows if row.is_billable)
        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded ICD-10-CM FY{fy}: {len(objects)} codes ({billable} billable), "
                f"{len(notes_map)} codes with tabular notes"
            )
        )
