"""Load the bundled synthetic notes from data/samples/ (idempotent by hash)."""

import hashlib
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from apps.notes.models import Note


class Command(BaseCommand):
    help = "Load synthetic sample notes into the database"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--path", type=Path, default=Path("../data/samples"))

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        path = Path(options["path"])
        loaded = skipped = 0
        for file in sorted(path.glob("*.txt")):
            text = file.read_text(encoding="utf-8")
            sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
            title = file.stem.replace("_", " ").capitalize()
            _, created = Note.objects.update_or_create(
                text_sha256=sha256,
                source=Note.Source.SAMPLE,
                defaults={"title": title, "text": text},
            )
            loaded += int(created)
            skipped += int(not created)
        self.stdout.write(
            self.style.SUCCESS(f"Samples: {loaded} loaded, {skipped} already present")
        )
