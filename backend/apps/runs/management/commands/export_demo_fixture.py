"""Export one completed run as the landing page's replay fixture."""

import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.runs.models import Run


class Command(BaseCommand):
    help = "Write a run's results to landing/src/demo.json for the static demo"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("run_id")
        parser.add_argument("--out", type=Path, default=Path("../landing/src/demo.json"))

    def handle(self, *args: Any, **options: Any) -> None:
        run = (
            Run.objects.select_related("note")
            .prefetch_related("conditions", "suggestions", "findings")
            .filter(id=options["run_id"])
            .first()
        )
        if run is None:
            raise CommandError("Unknown run id.")

        payload = {
            "note": {"title": run.note.title, "text": run.note.text},
            "mode": run.mode,
            "model_name": run.model_name,
            "conditions": [
                {
                    "id": c.id,
                    "label": c.label,
                    "status": c.status,
                    "quotes": c.quotes,
                }
                for c in run.conditions.all()
            ],
            "suggestions": [
                {
                    "display_code": s.display_code,
                    "description": s.description,
                    "hcc_number": s.hcc_number,
                    "hcc_label": s.hcc_label,
                    "evidence": s.evidence,
                    "meat": s.meat,
                    "confidence": s.confidence,
                    "confidence_reasons": s.confidence_reasons,
                    "rationale": s.rationale,
                    "flags": s.flags,
                    "condition_id": s.condition_id,
                }
                for s in run.suggestions.all()
            ],
            "findings": [
                {
                    "submitted_code": f.submitted_code,
                    "verdict": f.verdict,
                    "reason": f.reason,
                    "evidence": f.evidence,
                    "suggested_code": f.suggested_code,
                }
                for f in run.findings.all()
            ],
        }
        out: Path = options["out"]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Demo fixture written to {out}"))
