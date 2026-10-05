"""The /decisions trail and CSV exports."""

import csv
import io
from typing import Any

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.runs.models import Run
from tests.conftest import NOTE_TEXT, post_run

pytestmark = pytest.mark.django_db


@pytest.fixture
def decided_run(pipeline_env: None, client: Client, django_capture_on_commit_callbacks: Any) -> Run:
    response = post_run(client, django_capture_on_commit_callbacks, {"text": NOTE_TEXT})
    run = Run.objects.get(id=response.json()["run_id"])
    suggestions = {s.display_code: s for s in run.suggestions.all()}
    client.post(
        f"/api/suggestions/{suggestions['E11.22'].id}/decisions",
        {"action": "accept"},
        content_type="application/json",
    )
    client.post(
        f"/api/suggestions/{suggestions['N18.31'].id}/decisions",
        {"action": "reject", "reason": "stage not current"},
        content_type="application/json",
    )
    return run


class TestDecisionsTrail:
    def test_lists_decisions_with_reviewer_and_context(
        self, decided_run: Run, client: Client
    ) -> None:
        body = client.get("/api/decisions").json()
        assert body["count"] == 2
        actions = {item["original_code"]: item for item in body["items"]}
        assert actions["E11.22"]["action"] == "accept"
        assert actions["N18.31"]["reason"] == "stage not current"
        assert actions["E11.22"]["reviewer_name"]
        assert actions["E11.22"]["run_id"] == str(decided_run.id)
        assert actions["E11.22"]["kind"] == "suggestion"

    def test_filters(self, decided_run: Run, client: Client, user: User) -> None:
        assert client.get("/api/decisions?action=accept").json()["count"] == 1
        assert client.get("/api/decisions?code=e11.22").json()["count"] == 1
        assert client.get(f"/api/decisions?reviewer={user.username}").json()["count"] == 2
        assert client.get("/api/decisions?reviewer=nobody").json()["count"] == 0
        assert client.get(f"/api/decisions?run={decided_run.id}").json()["count"] == 2
        assert client.get("/api/decisions?date_from=2099-01-01T00:00:00Z").json()["count"] == 0


class TestCsvExports:
    def test_decisions_export(self, decided_run: Run, client: Client) -> None:
        response = client.get("/api/decisions/export.csv")
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"
        rows = list(csv.reader(io.StringIO(response.content.decode())))
        header, data = rows[0], rows[1:]
        assert "original_code" in header
        assert len(data) == 2
        by_code = {row[header.index("original_code")]: row for row in data}
        assert by_code["E11.22"][header.index("action")] == "accept"
        # The snapshot's evidence travels into the export.
        assert "Type 2 diabetes" in by_code["E11.22"][header.index("evidence_shown")]

    def test_decisions_export_respects_filters(self, decided_run: Run, client: Client) -> None:
        response = client.get("/api/decisions/export.csv?action=reject")
        rows = list(csv.reader(io.StringIO(response.content.decode())))
        assert len(rows) == 2  # header + 1

    def test_run_export(self, decided_run: Run, client: Client) -> None:
        response = client.get(f"/api/runs/{decided_run.id}/export.csv")
        rows = list(csv.reader(io.StringIO(response.content.decode())))
        header, data = rows[0], rows[1:]
        assert len(data) == 2  # two suggestions
        by_code = {row[header.index("code")]: row for row in data}
        assert by_code["E11.22"][header.index("decision")] == "accept"
        assert by_code["E11.22"][header.index("hcc")] == "37"
        assert by_code["N18.31"][header.index("decision")] == "reject"
