"""Load draft gold labels, non-codes, audit cases, and splits from the
samples manifest. Idempotent; everything loads with reviewed=False."""

import hashlib
import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction

from apps.evaluation.models import AuditCase, GoldLabel, GoldNonCode
from apps.notes.models import Note


class Command(BaseCommand):
    help = "Load draft answer-key labels from data/samples/manifest.json"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--path", type=Path, default=Path("../data/samples"))

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        path = Path(options["path"])
        manifest_path = path / "manifest.json"
        if not manifest_path.exists():
            raise CommandError(f"{manifest_path} not found.")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        labels = non_codes = cases = 0
        for entry in manifest:
            text = (path / entry["file"]).read_text(encoding="utf-8")
            sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
            note = Note.objects.filter(text_sha256=sha256, source=Note.Source.SAMPLE).first()
            if note is None:
                raise CommandError(f"{entry['file']} not loaded yet; run load_samples first.")
            note.title = entry.get("title", note.title)
            note.split = entry.get("split", "none")
            note.scenario_tags = entry.get("scenario_tags", [])
            note.save(update_fields=["title", "split", "scenario_tags"])

            for gold in entry.get("gold_labels", []):
                _, created = GoldLabel.objects.get_or_create(
                    note=note,
                    display_code=gold["display_code"].upper(),
                    defaults={"rationale": gold.get("rationale", "")},
                )
                labels += int(created)
            for non in entry.get("gold_non_codes", []):
                _, created = GoldNonCode.objects.get_or_create(
                    note=note,
                    condition_label=non["condition_label"],
                    reason=non["reason"],
                    defaults={"rationale": non.get("rationale", "")},
                )
                non_codes += int(created)
            case = entry.get("audit_case")
            if case:
                _, created = AuditCase.objects.get_or_create(
                    note=note,
                    defaults={
                        "submitted_codes": case["submitted_codes"],
                        "expected_verdicts": case["expected_verdicts"],
                    },
                )
                cases += int(created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Draft labels loaded: {labels} gold labels, {non_codes} non-codes, "
                f"{cases} audit cases (all reviewed=False — review them in the admin)"
            )
        )
