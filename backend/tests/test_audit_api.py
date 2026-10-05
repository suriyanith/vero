"""Audit-mode runs end to end through the API, worker, and review."""

from typing import Any

import pytest
from django.test import Client

from apps.review.models import ReviewDecision
from apps.runs.models import Run
from tests.conftest import NOTE_TEXT, post_run


@pytest.fixture
def audit_run(pipeline_env: None, client: Client, django_capture_on_commit_callbacks: Any) -> Run:
    response = post_run(
        client,
        django_capture_on_commit_callbacks,
        {
            "text": NOTE_TEXT,
            "mode": "audit",
            "submitted_codes": ["E11.9", "N18.31", "I50.9", "X99.99"],
        },
    )
    assert response.status_code == 202
    return Run.objects.get(id=response.json()["run_id"])


@pytest.mark.django_db
class TestAuditLifecycle:
    def test_verdicts_end_to_end(self, audit_run: Run, client: Client) -> None:
        detail = client.get(f"/api/runs/{audit_run.id}").json()
        assert detail["status"] == "ready_for_review"
        assert detail["mode"] == "audit"
        by_code = {f["submitted_code"]: f for f in detail["findings"] if f["submitted_code"]}

        # E11.9 is in the E11 family but the note supports the combination code.
        assert by_code["E11.9"]["verdict"] == "SPECIFICITY_MISMATCH"
        assert by_code["E11.9"]["suggested_code"] == "E11.22"
        # N18.31 matches a suggestion with MEAT.
        assert by_code["N18.31"]["verdict"] == "SUPPORTED"
        assert by_code["N18.31"]["evidence"][0]["text"] == "eGFR stable at 52"
        # Heart failure is only "rule out" in the note.
        assert by_code["I50.9"]["verdict"] == "NOT_SUPPORTED"
        assert by_code["I50.9"]["reason_code"] == "UNCERTAIN"
        # X99.99 is not a real code.
        assert by_code["X99.99"]["verdict"] == "INVALID_CODE"

        # E11.22 was already offered as the fix for E11.9; N18.31 was
        # submitted — so no missed HCCs.
        assert not [f for f in detail["findings"] if f["verdict"] == "MISSED_HCC"]

    def test_missed_hcc_when_nothing_submitted_covers_it(
        self, pipeline_env: None, client: Client, django_capture_on_commit_callbacks: Any
    ) -> None:
        response = post_run(
            client,
            django_capture_on_commit_callbacks,
            {"text": NOTE_TEXT, "mode": "audit", "submitted_codes": ["I10"]},
        )
        detail = client.get(f"/api/runs/{response.json()['run_id']}").json()
        missed = [f for f in detail["findings"] if f["verdict"] == "MISSED_HCC"]
        assert {f["suggested_code"] for f in missed} == {"E11.22", "N18.31"}

    def test_audit_requires_submitted_codes(self, pipeline_env: None, client: Client) -> None:
        response = client.post(
            "/api/runs",
            {"text": NOTE_TEXT, "mode": "audit", "submitted_codes": []},
            content_type="application/json",
        )
        assert response.json()["error"]["code"] == "SUBMITTED_CODES_REQUIRED"

    def test_batches_stay_coding_only(self, pipeline_env: None, client: Client) -> None:
        from django.core.files.uploadedfile import SimpleUploadedFile

        files = [SimpleUploadedFile("a.txt", NOTE_TEXT.encode(), "text/plain")]
        response = client.post("/api/batches", {"mode": "audit", "files": files})
        assert response.json()["error"]["code"] == "BATCH_AUDIT_UNSUPPORTED"


@pytest.mark.django_db
class TestFindingDecisions:
    def test_accept_finding_snapshots_and_resolves_code(
        self, audit_run: Run, client: Client
    ) -> None:
        mismatch = audit_run.findings.get(submitted_code="E11.9")
        response = client.post(
            f"/api/findings/{mismatch.id}/decisions",
            {"action": "accept"},
            content_type="application/json",
        )
        assert response.status_code == 201
        # Accepting a specificity mismatch endorses the suggested code.
        assert response.json()["final_code"] == "E11.22"
        decision = ReviewDecision.objects.get(finding=mismatch)
        assert decision.evidence_snapshot["verdict"] == "SPECIFICITY_MISMATCH"
        assert decision.original_code == "E11.9"

    def test_reject_and_modify_findings(self, audit_run: Run, client: Client) -> None:
        supported = audit_run.findings.get(submitted_code="N18.31")
        rejected = client.post(
            f"/api/findings/{supported.id}/decisions",
            {"action": "reject", "reason": "disagree"},
            content_type="application/json",
        )
        assert rejected.status_code == 201

        invalid = audit_run.findings.get(submitted_code="X99.99")
        modified = client.post(
            f"/api/findings/{invalid.id}/decisions",
            {"action": "modify", "final_code": "E11.21"},
            content_type="application/json",
        )
        assert modified.status_code == 201
        assert modified.json()["final_code"] == "E11.21"

    def test_audit_run_completes_when_all_findings_decided(
        self, audit_run: Run, client: Client
    ) -> None:
        for finding in audit_run.findings.all():
            client.post(
                f"/api/findings/{finding.id}/decisions",
                {"action": "accept"},
                content_type="application/json",
            )
        audit_run.refresh_from_db()
        assert audit_run.status == Run.Status.COMPLETED

    def test_latest_decision_shown_on_findings(self, audit_run: Run, client: Client) -> None:
        finding = audit_run.findings.get(submitted_code="I50.9")
        client.post(
            f"/api/findings/{finding.id}/decisions",
            {"action": "accept"},
            content_type="application/json",
        )
        detail = client.get(f"/api/runs/{audit_run.id}").json()
        shown = next(f for f in detail["findings"] if f["submitted_code"] == "I50.9")
        assert shown["latest_decision"]["action"] == "accept"
