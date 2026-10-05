"""End-to-end run lifecycle through the API with the immediate task backend."""

from typing import Any

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from apps.runs.models import Run
from tests.conftest import NOTE_TEXT, post_run


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
        # session + user + run + conditions + suggestions + their decisions
        # + findings (its decisions prefetch is free when no findings exist)
        with django_assert_num_queries(7):
            client.get(f"/api/runs/{run_id}")
