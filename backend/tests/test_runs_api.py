"""End-to-end run lifecycle through the API with the immediate task backend."""

from collections.abc import Iterator
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from apps.runs.models import Run
from tests.test_loaders import load_fixture_code_set, load_fixture_hcc_map
from vero_core.fake_llm import FakeLLMClient
from vero_core.schemas import (
    Certainty,
    CodeChoice,
    ConditionSelection,
    ConditionStatus,
    ExtractedCondition,
    ExtractedQuote,
    ExtractionResult,
    Meat,
    SelectionResult,
)

NOTE_TEXT = (
    "HPI: 72-year-old with type 2 diabetes and CKD stage 3a.\n"
    "Assessment:\n"
    "1. Type 2 diabetes with CKD stage 3a - continue metformin, eGFR stable at 52.\n"
    "2. Rule out heart failure. Order echocardiogram.\n"
)

EXTRACTION = ExtractionResult(
    conditions=[
        ExtractedCondition(
            label="type 2 diabetes mellitus with diabetic chronic kidney disease",
            status=ConditionStatus.ACTIVE,
            quotes=[
                ExtractedQuote(
                    text="Type 2 diabetes with CKD stage 3a - continue metformin",
                    meat=[Meat.TREAT, Meat.ASSESS],
                )
            ],
            specificity_details=[],
        ),
        ExtractedCondition(
            label="chronic kidney disease stage 3a",
            status=ConditionStatus.ACTIVE,
            quotes=[ExtractedQuote(text="eGFR stable at 52", meat=[Meat.EVALUATE])],
            specificity_details=[],
        ),
        ExtractedCondition(
            label="heart failure",
            status=ConditionStatus.UNCERTAIN,
            quotes=[ExtractedQuote(text="Rule out heart failure", meat=[])],
            specificity_details=[],
        ),
    ]
)

SELECTION = SelectionResult(
    selections=[
        ConditionSelection(
            condition_index=1,
            codes=[CodeChoice(code="E11.22", rationale="combination code applies")],
            no_fit=False,
            specificity_flags=[],
            certainty=Certainty.HIGH,
        ),
        ConditionSelection(
            condition_index=2,
            codes=[CodeChoice(code="N18.31", rationale="stage 3a documented")],
            no_fit=False,
            specificity_flags=[],
            certainty=Certainty.HIGH,
        ),
    ]
)


@pytest.fixture
def pipeline_env(db: None, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Fixture code set + a canned LLM so runs process fully offline."""
    load_fixture_code_set()
    load_fixture_hcc_map()
    monkeypatch.setattr(
        "apps.runs.tasks.build_llm_client",
        lambda run_id=None: FakeLLMClient(responses={"extract": EXTRACTION, "select": SELECTION}),
    )
    yield


def post_run(
    client: Client, django_capture_on_commit_callbacks: Any, payload: dict[str, Any]
) -> Any:
    # The task is enqueued on commit; executing the callbacks runs it
    # synchronously through the immediate backend.
    with django_capture_on_commit_callbacks(execute=True):
        response = client.post("/api/runs", payload, content_type="application/json")
    return response


class TestRunLifecycle:
    def test_run_processes_end_to_end(
        self, pipeline_env: None, client: Client, django_capture_on_commit_callbacks: Any
    ) -> None:
        response = post_run(
            client, django_capture_on_commit_callbacks, {"text": NOTE_TEXT, "mode": "coding"}
        )
        assert response.status_code == 202
        run_id = response.json()["run_id"]

        detail = client.get(f"/api/runs/{run_id}").json()
        assert detail["status"] == "ready_for_review"
        codes = {s["display_code"] for s in detail["suggestions"]}
        assert codes == {"E11.22", "N18.31"}
        e1122 = next(s for s in detail["suggestions"] if s["display_code"] == "E11.22")
        assert e1122["hcc_number"] == 37
        # Evidence offsets must slice the note text exactly.
        for quote in e1122["evidence"]:
            assert detail["note"]["text"][quote["start"] : quote["end"]] == quote["text"]
        statuses = {c["label"]: c["status"] for c in detail["conditions"]}
        assert statuses["heart failure"] == "uncertain"

    def test_run_from_sample_note(
        self, pipeline_env: None, client: Client, django_capture_on_commit_callbacks: Any
    ) -> None:
        from django.core.management import call_command

        call_command("load_samples", path="../data/samples")
        samples = client.get("/api/samples").json()
        assert len(samples) == 3
        response = post_run(
            client, django_capture_on_commit_callbacks, {"sample_id": samples[0]["id"]}
        )
        assert response.status_code == 202

    def test_phi_note_rejected(self, pipeline_env: None, client: Client) -> None:
        response = client.post(
            "/api/runs",
            {"text": "Patient DOB: 01/02/1950 with diabetes."},
            content_type="application/json",
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "PHI_DETECTED"
        assert Run.objects.count() == 0

    def test_oversized_note_rejected(self, pipeline_env: None, client: Client) -> None:
        response = client.post("/api/runs", {"text": "x" * 20001}, content_type="application/json")
        assert response.json()["error"]["code"] == "INPUT_TOO_LARGE"

    def test_audit_mode_not_yet_available(self, pipeline_env: None, client: Client) -> None:
        response = client.post(
            "/api/runs",
            {"text": NOTE_TEXT, "mode": "audit", "submitted_codes": ["E11.9"]},
            content_type="application/json",
        )
        assert response.json()["error"]["code"] == "AUDIT_NOT_AVAILABLE"

    def test_audit_mode_validates_code_format(self, pipeline_env: None, client: Client) -> None:
        response = client.post(
            "/api/runs",
            {"text": NOTE_TEXT, "mode": "audit", "submitted_codes": ["banana"]},
            content_type="application/json",
        )
        assert response.json()["error"]["code"] == "INVALID_CODE_FORMAT"

    def test_retry_only_failed_runs(
        self, pipeline_env: None, client: Client, django_capture_on_commit_callbacks: Any
    ) -> None:
        response = post_run(client, django_capture_on_commit_callbacks, {"text": NOTE_TEXT})
        run_id = response.json()["run_id"]
        assert client.post(f"/api/runs/{run_id}/retry").json()["error"]["code"] == "NOT_RETRYABLE"

        Run.objects.filter(id=run_id).update(status=Run.Status.FAILED)
        with django_capture_on_commit_callbacks(execute=True):
            retry = client.post(f"/api/runs/{run_id}/retry")
        assert retry.status_code == 202
        new_run = Run.objects.get(id=retry.json()["run_id"])
        assert str(new_run.retry_of_id) == run_id
        assert new_run.status == Run.Status.READY_FOR_REVIEW


class TestBatches:
    def test_batch_of_five_completes(
        self, pipeline_env: None, client: Client, django_capture_on_commit_callbacks: Any
    ) -> None:
        files = [
            SimpleUploadedFile(f"note_{i}.txt", NOTE_TEXT.encode(), "text/plain") for i in range(5)
        ]
        with django_capture_on_commit_callbacks(execute=True):
            response = client.post("/api/batches", {"mode": "coding", "files": files})
        assert response.status_code == 202
        body = response.json()
        assert len(body["run_ids"]) == 5
        assert body["rejected"] == []
        assert Run.objects.filter(status=Run.Status.READY_FOR_REVIEW).count() == 5

    def test_bad_files_rejected_good_ones_kept(
        self, pipeline_env: None, client: Client, django_capture_on_commit_callbacks: Any
    ) -> None:
        files = [
            SimpleUploadedFile("good.txt", NOTE_TEXT.encode(), "text/plain"),
            SimpleUploadedFile("scan.pdf", b"%PDF-", "application/pdf"),
            SimpleUploadedFile("binary.txt", b"\xff\xfe\x00bad", "text/plain"),
            SimpleUploadedFile("phi.txt", b"MRN: 1234 diabetes", "text/plain"),
        ]
        with django_capture_on_commit_callbacks(execute=True):
            response = client.post("/api/batches", {"mode": "coding", "files": files})
        body = response.json()
        assert len(body["run_ids"]) == 1
        rejected = {r["filename"]: r["code"] for r in body["rejected"]}
        assert rejected == {
            "scan.pdf": "NOT_TXT",
            "binary.txt": "NOT_UTF8",
            "phi.txt": "PHI_DETECTED",
        }


class TestListAndQueries:
    def test_work_queue_filters_and_pagination(
        self, pipeline_env: None, client: Client, django_capture_on_commit_callbacks: Any
    ) -> None:
        for _ in range(3):
            post_run(client, django_capture_on_commit_callbacks, {"text": NOTE_TEXT})
        body = client.get("/api/runs?limit=2&mine=true").json()
        assert body["count"] == 3
        assert len(body["items"]) == 2
        assert body["items"][0]["suggestion_count"] == 2

        none_queued = client.get("/api/runs?status=queued").json()
        assert none_queued["count"] == 0

    def test_run_detail_query_count_is_fixed(
        self,
        pipeline_env: None,
        client: Client,
        django_capture_on_commit_callbacks: Any,
        django_assert_num_queries: Any,
    ) -> None:
        response = post_run(client, django_capture_on_commit_callbacks, {"text": NOTE_TEXT})
        run_id = response.json()["run_id"]
        client.get(f"/api/runs/{run_id}")  # warm up session queries
        # session + user + run + conditions + suggestions
        with django_assert_num_queries(5):
            client.get(f"/api/runs/{run_id}")
