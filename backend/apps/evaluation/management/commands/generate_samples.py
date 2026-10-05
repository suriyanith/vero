"""Draft synthetic notes with Gemini, to be reviewed by a person.

Each draft covers 3-6 conditions from the scenario matrix with mixed
documentation patterns, is written as an outpatient SOAP note with no
identifiers, and is saved under data/samples/ plus a manifest entry carrying
the generator's intended codes as DRAFT gold labels (reviewed=false).
Generated labels are never treated as correct until a person reviews them.
"""

import json
import random
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from pydantic import BaseModel

from apps.llm.gemini import GeminiClient

CONDITIONS = [
    "type 2 diabetes without complications",
    "type 2 diabetes with diabetic chronic kidney disease",
    "chronic kidney disease stage 3a",
    "chronic kidney disease stage 4",
    "chronic systolic heart failure",
    "COPD",
    "atrial fibrillation",
    "major depressive disorder recurrent",
    "morbid obesity",
    "peripheral vascular disease",
    "hypertension",
    "hyperlipidemia",
    "GERD",
]

PATTERNS = [
    "WELL_DOCUMENTED",
    "HISTORY_ONLY",
    "RESOLVED",
    "RULE_OUT",
    "NEGATED",
    "FAMILY_HISTORY",
    "PROBLEM_LIST_ONLY",
    "VAGUE",
    "PRESUMED_LINK",
    "MESSY",
]


class DraftGold(BaseModel):
    display_code: str
    rationale: str


class DraftNote(BaseModel):
    title: str
    note_text: str
    scenario_tags: list[str]
    intended_codes: list[DraftGold]
    intended_non_codes: list[str]  # "condition | reason" pairs


class Command(BaseCommand):
    help = "Draft synthetic notes with Gemini (requires GEMINI_API_KEY; human review required)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--count", type=int, default=40)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--out", type=Path, default=Path("../data/samples"))

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.GEMINI_API_KEY or settings.VERO_LLM_MODE != "live":
            raise CommandError("generate_samples needs VERO_LLM_MODE=live and GEMINI_API_KEY set.")
        rng = random.Random(options["seed"])
        client = GeminiClient.from_settings()
        out: Path = options["out"]
        manifest_path = out / "manifest.json"
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else []
        existing = len(manifest)

        for index in range(options["count"]):
            conditions = rng.sample(CONDITIONS, k=rng.randint(3, 6))
            patterns = rng.sample(PATTERNS, k=min(len(conditions), 4))
            result = client.generate(
                step="extract",  # reuse the extract logging bucket
                prompt_id="generate_note",
                prompt_version="v1",
                variables={
                    "conditions": ", ".join(conditions),
                    "patterns": ", ".join(patterns),
                },
                output_model=DraftNote,
            )
            draft = result.parsed
            assert isinstance(draft, DraftNote)
            number = existing + index + 1
            filename = f"note_{number:02d}_generated.txt"
            (out / filename).write_text(draft.note_text, encoding="utf-8")
            manifest.append(
                {
                    "file": filename,
                    "title": draft.title,
                    "split": "none",  # assigned after review (assign_splits)
                    "scenario_tags": draft.scenario_tags,
                    "gold_labels": [
                        {"display_code": g.display_code, "rationale": g.rationale}
                        for g in draft.intended_codes
                    ],
                    "gold_non_codes": [
                        {
                            "condition_label": pair.split("|")[0].strip(),
                            "reason": pair.split("|")[1].strip() if "|" in pair else "no_meat",
                        }
                        for pair in draft.intended_non_codes
                    ],
                    "audit_case": None,
                }
            )
            self.stdout.write(f"  drafted {filename}: {draft.title}")

        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        self.stdout.write(
            self.style.WARNING(
                "Drafts written. Review every note and label before trusting anything: "
                "load with load_samples + load_gold_drafts, then review in the admin."
            )
        )
