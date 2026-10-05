"""run_eval end to end on the fixture code set with the canned LLM."""

import hashlib
from typing import Any

import pytest
from django.core.management import CommandError, call_command
from django.test import Client

from apps.accounts.models import User
from apps.evaluation.models import AuditCase, EvalRun, GoldLabel, GoldNonCode
from apps.notes.models import Note
from tests.conftest import NOTE_TEXT

pytestmark = pytest.mark.django_db


@pytest.fixture
def labeled_split(pipeline_env: None, monkeypatch: pytest.MonkeyPatch) -> Note:
    """One test-split note whose canned pipeline answers are exactly right."""
    monkeypatch.setattr(
        "apps.evaluation.services.build_llm_client",
        __import__("apps.runs.tasks", fromlist=["build_llm_client"]).build_llm_client,
    )
    note = Note.objects.create(
        title="eval note",
        text=NOTE_TEXT,
        text_sha256=hashlib.sha256(NOTE_TEXT.encode()).hexdigest(),
        source=Note.Source.SAMPLE,
        split=Note.Split.TEST,
    )
    for code in ("E11.22", "N18.31"):
        GoldLabel.objects.create(note=note, display_code=code, reviewed=True)
    GoldNonCode.objects.create(
        note=note, condition_label="heart failure", reason="uncertain", reviewed=True
    )
    AuditCase.objects.create(
        note=note,
        submitted_codes=["E11.9", "N18.31", "I50.9"],
        expected_verdicts={
            "E11.9": "SPECIFICITY_MISMATCH",
            "N18.31": "SUPPORTED",
            "I50.9": "NOT_SUPPORTED",
        },
        reviewed=True,
    )
    return note


class TestRunEval:
    def test_perfect_pipeline_scores_perfectly(self, labeled_split: Note) -> None:
        call_command("run_eval", split="test", mode="both")
        eval_run = EvalRun.objects.get()
        assert not eval_run.provisional

        coding = eval_run.metrics["coding"]
        assert coding["code_level"]["f1"] == 1.0
        assert coding["hard_cases"]["uncertain"]["accuracy"] == 1.0
        assert coding["evidence_integrity"]["unverified_quotes_shown"] == 0
        assert coding["evidence_integrity"]["invalid_codes_shown"] == 0
        assert coding["operational"]["success_rate"] == 1.0

        audit = eval_run.metrics["audit"]
        assert audit["overall_accuracy"] == 1.0
        assert audit["unsupported_caught_rate"] == 1.0

    def test_refuses_unreviewed_labels(self, labeled_split: Note) -> None:
        GoldLabel.objects.update(reviewed=False)
        with pytest.raises(CommandError, match="unreviewed"):
            call_command("run_eval", split="test", mode="coding")

    def test_allow_unreviewed_marks_provisional(self, labeled_split: Note) -> None:
        GoldLabel.objects.update(reviewed=False)
        call_command("run_eval", split="test", mode="coding", allow_unreviewed=True)
        assert EvalRun.objects.get().provisional

    def test_empty_split_fails_clearly(self, pipeline_env: None) -> None:
        with pytest.raises(CommandError, match="No notes"):
            call_command("run_eval", split="dev", mode="coding")


class TestEvalApi:
    def test_admin_only(self, labeled_split: Note, client: Client) -> None:
        call_command("run_eval", split="test", mode="coding")
        assert client.get("/api/eval/runs").status_code == 403

    def test_admin_sees_runs(self, labeled_split: Note, admin_user: User) -> None:
        call_command("run_eval", split="test", mode="coding")
        admin_client = Client()
        admin_client.force_login(admin_user)
        runs = admin_client.get("/api/eval/runs").json()
        assert len(runs) == 1
        detail = admin_client.get(f"/api/eval/runs/{runs[0]['id']}").json()
        assert detail["metrics"]["coding"]["code_level"]["f1"] == 1.0


class TestGoldDraftLoading:
    def test_manifest_round_trip(self, db: None, tmp_path: Any) -> None:
        import json
        from pathlib import Path

        samples = Path(tmp_path)
        (samples / "a.txt").write_text("note text here")
        (samples / "manifest.json").write_text(
            json.dumps(
                [
                    {
                        "file": "a.txt",
                        "title": "A",
                        "split": "dev",
                        "scenario_tags": ["VAGUE"],
                        "gold_labels": [{"display_code": "e11.9", "rationale": "r"}],
                        "gold_non_codes": [{"condition_label": "x", "reason": "negated"}],
                        "audit_case": {
                            "submitted_codes": ["E11.9"],
                            "expected_verdicts": {"E11.9": "SUPPORTED"},
                        },
                    }
                ]
            )
        )
        call_command("load_samples", path=str(samples))
        call_command("load_gold_drafts", path=str(samples))
        call_command("load_gold_drafts", path=str(samples))  # idempotent

        note = Note.objects.get(source=Note.Source.SAMPLE)
        assert note.split == "dev"
        assert note.scenario_tags == ["VAGUE"]
        label = GoldLabel.objects.get()
        assert label.display_code == "E11.9"
        assert not label.reviewed
        assert GoldNonCode.objects.count() == 1
        assert AuditCase.objects.count() == 1

    def test_real_manifest_loads(self, db: None) -> None:
        call_command("load_samples", path="../data/samples")
        call_command("load_gold_drafts", path="../data/samples")
        assert Note.objects.filter(split="test").count() == 8
        assert Note.objects.filter(split="dev").count() == 4
        assert GoldLabel.objects.count() > 20
        assert AuditCase.objects.count() == 4
        assert not GoldLabel.objects.filter(reviewed=True).exists()
