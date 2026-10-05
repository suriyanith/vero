"""Load an ICD-10 → CMS-HCC mapping release plus its HCC labels."""

import hashlib
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction

from apps.reference.models import CodeSetVersion, HccCategory, HccModel, Icd10HccMap
from apps.reference.parsers import parse_hcc_labels, parse_hcc_mappings_csv

CMS_RA_URL = (
    "https://www.cms.gov/medicare/payment/medicare-advantage-rates-statistics/risk-adjustment"
)


class Command(BaseCommand):
    help = "Load an ICD-10 to CMS-HCC mapping (CSV) and HCC labels (SAS LABEL file)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--model", default="V28", help="Model version column, e.g. V28")
        parser.add_argument("--payment-year", type=int, required=True)
        parser.add_argument("--file", type=Path, required=True, help="Mappings CSV")
        parser.add_argument("--labels-file", type=Path, required=True, help="e.g. V28115L3.TXT")
        parser.add_argument("--source-url", default=CMS_RA_URL)

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        code_set = CodeSetVersion.objects.filter(is_active=True).first()
        if code_set is None:
            raise CommandError("Load an ICD-10-CM code set first (load_icd10cm).")

        version: str = options["model"]
        labels = parse_hcc_labels(options["labels_file"])
        pairs = parse_hcc_mappings_csv(options["file"], version=version)
        sha256 = hashlib.sha256(options["file"].read_bytes()).hexdigest()

        model, _ = HccModel.objects.update_or_create(
            name="CMS-HCC",
            version=version,
            payment_year=options["payment_year"],
            defaults={"source_url": options["source_url"], "sha256": sha256, "is_active": True},
        )
        HccModel.objects.exclude(pk=model.pk).update(is_active=False)
        model.categories.all().delete()  # cascades to mappings

        categories = HccCategory.objects.bulk_create(
            HccCategory(model=model, number=number, label=label)
            for number, label in sorted(labels.items())
        )
        by_number = {category.number: category for category in categories}

        missing_labels = {number for _, number in pairs} - set(by_number)
        if missing_labels:
            raise CommandError(f"Mapping references HCCs with no label: {sorted(missing_labels)}")

        Icd10HccMap.objects.bulk_create(
            (
                Icd10HccMap(model=model, code_set=code_set, code=code, hcc=by_number[number])
                for code, number in pairs
            ),
            batch_size=5000,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded CMS-HCC {version} PY{options['payment_year']}: "
                f"{len(by_number)} categories, {len(pairs)} code mappings"
            )
        )
