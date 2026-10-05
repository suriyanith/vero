"""Evaluate the pipeline against the labeled answer key.

Reruns are free: the LLM cache answers repeated calls without touching the
API. Results are stored as an EvalRun and summarized on stdout.
"""

import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.evaluation.services import EvalError, run_evaluation


class Command(BaseCommand):
    help = "Run the evaluation on a labeled split and store an EvalRun"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--split", choices=["dev", "test"], default="test")
        parser.add_argument("--mode", choices=["coding", "audit", "both"], default="both")
        parser.add_argument(
            "--allow-unreviewed",
            action="store_true",
            help="Run even if labels are unreviewed; results are marked provisional",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            eval_run = run_evaluation(
                split=options["split"],
                mode=options["mode"],
                allow_unreviewed=options["allow_unreviewed"],
            )
        except EvalError as exc:
            raise CommandError(str(exc)) from exc

        flag = " (PROVISIONAL — unreviewed labels)" if eval_run.provisional else ""
        self.stdout.write(
            self.style.SUCCESS(f"EvalRun {eval_run.id} on {eval_run.split} [{eval_run.mode}]{flag}")
        )
        self.stdout.write(json.dumps(eval_run.metrics, indent=2, default=str))
