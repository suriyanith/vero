from typing import Any

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.review.models import AppendOnlyError, ReviewDecision
from apps.review.services import accept_all_high
from apps.runs.models import Run, Suggestion
from tests.conftest import NOTE_TEXT, post_run


@pytest.fixture
def reviewed_run(
    pipeline_env: None, client: Client, django_capture_on_commit_callbacks: Any
) -> Run:
    response = post_run(client, django_capture_on_commit_callbacks, {"text": NOTE_TEXT})
    return Run.objects.get(id=response.json()["run_id"])


def decide(client: Client, suggestion_id: int, payload: dict[str, Any]) -> Any:
    return client.post(
        f"/api/suggestions/{suggestion_id}/decisions", payload, content_type="application/json"
    )


@pytest.mark.django_db
class TestAppendOnly:
    def test_update_and_delete_raise(self, reviewed_run: Run, user: User) -> None:
        suggestion = reviewed_run.suggestions.first()
        assert suggestion is not None
        decision = ReviewDecision.objects.create(
            run=reviewed_run,
            suggestion=suggestion,
            reviewer=user,
            action="accept",
            original_code=suggestion.display_code,
        )
        decision.reason = "edited"
        with pytest.raises(AppendOnlyError):
            decision.save()
        with pytest.raises(AppendOnlyError):
            decision.delete()


@pytest.mark.django_db
class TestDecisionEndpoint:
    def test_accept_builds_evidence_snapshot(self, reviewed_run: Run, client: Client) -> None:
        suggestion = reviewed_run.suggestions.get(display_code="E11.22")
        response = decide(client, suggestion.id, {"action": "accept"})
        assert response.status_code == 201
        decision = ReviewDecision.objects.get(suggestion=suggestion)
        assert decision.final_code == "E11.22"
        snapshot = decision.evidence_snapshot
        assert snapshot["display_code"] == "E11.22"
        assert snapshot["confidence"] == suggestion.confidence
        assert snapshot["evidence"] == suggestion.evidence

    def test_reject_with_reason(self, reviewed_run: Run, client: Client) -> None:
        suggestion = reviewed_run.suggestions.first()
        assert suggestion is not None
        response = decide(
            client, suggestion.id, {"action": "reject", "reason": "not supported today"}
        )
        assert response.status_code == 201
        assert response.json()["reason"] == "not supported today"
        assert response.json()["final_code"] == ""

    def test_modify_requires_billable_code(self, reviewed_run: Run, client: Client) -> None:
        suggestion = reviewed_run.suggestions.get(display_code="E11.22")
        no_code = decide(client, suggestion.id, {"action": "modify"})
        assert no_code.json()["error"]["code"] == "FINAL_CODE_REQUIRED"

        header = decide(client, suggestion.id, {"action": "modify", "final_code": "E11"})
        assert header.json()["error"]["code"] == "INVALID_FINAL_CODE"

        ok = decide(client, suggestion.id, {"action": "modify", "final_code": "e11.21"})
        assert ok.status_code == 201
        assert ok.json()["final_code"] == "E11.21"

    def test_changing_your_mind_appends_a_new_row(self, reviewed_run: Run, client: Client) -> None:
        suggestion = reviewed_run.suggestions.get(display_code="E11.22")
        decide(client, suggestion.id, {"action": "accept"})
        decide(client, suggestion.id, {"action": "reject", "reason": "second thoughts"})
        decisions = ReviewDecision.objects.filter(suggestion=suggestion)
        assert decisions.count() == 2

        detail = client.get(f"/api/runs/{reviewed_run.id}").json()
        shown = next(s for s in detail["suggestions"] if s["display_code"] == "E11.22")
        assert shown["latest_decision"]["action"] == "reject"

    def test_run_completes_when_all_suggestions_decided(
        self, reviewed_run: Run, client: Client
    ) -> None:
        suggestions = list(reviewed_run.suggestions.all())
        assert len(suggestions) == 2
        decide(client, suggestions[0].id, {"action": "accept"})
        reviewed_run.refresh_from_db()
        assert reviewed_run.status == Run.Status.READY_FOR_REVIEW
        decide(client, suggestions[1].id, {"action": "reject"})
        reviewed_run.refresh_from_db()
        assert reviewed_run.status == Run.Status.COMPLETED

    def test_decision_rejected_while_run_is_processing(
        self, reviewed_run: Run, client: Client
    ) -> None:
        suggestion = reviewed_run.suggestions.first()
        assert suggestion is not None
        Run.objects.filter(id=reviewed_run.id).update(status=Run.Status.PROCESSING)
        response = decide(client, suggestion.id, {"action": "accept"})
        assert response.json()["error"]["code"] == "RUN_NOT_REVIEWABLE"


@pytest.mark.django_db
class TestAcceptAllHigh:
    def test_accepts_only_undecided_high(
        self, reviewed_run: Run, client: Client, user: User
    ) -> None:
        # Make one suggestion Medium so it must be left alone.
        medium = reviewed_run.suggestions.get(display_code="N18.31")
        Suggestion.objects.filter(id=medium.id).update(confidence=Suggestion.Confidence.MEDIUM)
        response = client.post(f"/api/runs/{reviewed_run.id}/accept-high")
        assert response.status_code == 200
        assert response.json()["accepted"] == 1
        assert ReviewDecision.objects.filter(suggestion__display_code="E11.22").exists()
        assert not ReviewDecision.objects.filter(suggestion=medium).exists()

        # Idempotent: a second call finds nothing undecided.
        again = client.post(f"/api/runs/{reviewed_run.id}/accept-high")
        assert again.json()["accepted"] == 0

    def test_completes_run_when_everything_was_high(self, reviewed_run: Run, user: User) -> None:
        accept_all_high(reviewed_run, user)
        reviewed_run.refresh_from_db()
        assert reviewed_run.status == Run.Status.COMPLETED
