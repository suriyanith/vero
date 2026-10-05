"""Mark runs stuck in processing as failed (e.g. after a worker crash)."""

from datetime import timedelta
from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django.utils import timezone

from apps.runs.models import Run


class Command(BaseCommand):
    help = "Fail runs stuck in processing for longer than --older-than minutes"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--older-than", type=int, default=15, metavar="MINUTES")

    def handle(self, *args: Any, **options: Any) -> None:
        cutoff = timezone.now() - timedelta(minutes=options["older_than"])
        updated = Run.objects.filter(status=Run.Status.PROCESSING, started_at__lt=cutoff).update(
            status=Run.Status.FAILED,
            finished_at=timezone.now(),
            error_code="WORKER_TIMEOUT",
            error_message="Processing took too long and was stopped. Retry the run.",
        )
        self.stdout.write(self.style.SUCCESS(f"Marked {updated} stuck run(s) as failed"))
