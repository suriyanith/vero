"""Run the coding pipeline on note files against the real Gemini API.

This is the manual live-smoke entry point (`make live-smoke`). Automated
tests never call the real API.
"""

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.llm.gemini import GeminiClient
from apps.reference.services import PostgresCodeRepository
from vero_core.interfaces import PipelineConfig, PipelineDeps
from vero_core.pipeline import code_note


class Command(BaseCommand):
    help = "Code one or more note files with the live Gemini API (manual smoke test)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("notes", nargs="+", type=Path)

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            repo = PostgresCodeRepository()
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        client = GeminiClient.from_settings()
        deps = PipelineDeps(llm=client, codes=repo)
        config = PipelineConfig(model_name=client.model_name)

        for path in options["notes"]:
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n=== {path.name} ==="))
            result = code_note(path.read_text(encoding="utf-8"), deps, config)

            for s in result.suggestions:
                hcc = f"HCC {s.hcc_number}" if s.hcc_number else "no HCC"
                flags = f"  flags={','.join(s.flags)}" if s.flags else ""
                self.stdout.write(
                    f"  {s.code:<9} {s.confidence.value:<6} {hcc:<8} "
                    f"rank={s.candidate_rank}{flags}  {s.description[:60]}"
                )
                for quote in s.evidence:
                    self.stdout.write(f'      "{quote.text}" [{quote.match_type}]')
            for condition in result.not_coded:
                self.stdout.write(f"  not coded ({condition.status.value}): {condition.label}")
            for item in result.dropped:
                self.stdout.write(f"  dropped ({item.reason}): {item.label}")
            usage = result.usage
            self.stdout.write(
                f"  tokens in/out: {usage.input_tokens}/{usage.output_tokens}, "
                f"{usage.duration_ms} ms, dropped quotes: {usage.dropped_quotes}"
            )
