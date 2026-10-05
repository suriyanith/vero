"""Every dashboard metric checked against hand-computed values on seeded data."""

from datetime import datetime, timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.dashboard import services
from apps.llm.models import LlmCall
from apps.notes.models import Note
from apps.review.models import ReviewDecision
from apps.runs.models import AuditFinding, Run, Suggestion

pytestmark = pytest.mark.django_db


@pytest.fixture
def seeded(user: User) -> User:
    """A small, fully hand-countable world.

    Runs: 2 ready_for_review, 1 completed, 1 failed (LLM_RATE_LIMITED),
    1 queued. Suggestions: 4 total; 3 decided (latest: accept High-HCC,
    reject Medium, modify Low-HCC), 1 undecided. Findings: NOT_SUPPORTED,
    INVALID_CODE, MISSED_HCC. LLM calls: 4 (1 cache hit), 100/50 tokens each.
    """
    note = Note.objects.create(
        title="n", text="t", text_sha256="x", source=Note.Source.USER, created_by=user
    )

    def run(status: str, duration: int | None = None, error: str = "") -> Run:
        return Run.objects.create(
            note=note,
            mode="coding",
            created_by=user,
            status=status,
            duration_ms=duration,
            error_code=error,
        )

    r1 = run(Run.Status.READY_FOR_REVIEW, duration=1000)
    r2 = run(Run.Status.READY_FOR_REVIEW, duration=3000)
    r3 = run(Run.Status.COMPLETED, duration=2000)
    run(Run.Status.FAILED, error="LLM_RATE_LIMITED")
    run(Run.Status.QUEUED)

    def suggestion(run_obj: Run, code: str, confidence: str, hcc: int | None) -> Suggestion:
        return Suggestion.objects.create(
            run=run_obj,
            display_code=code,
            description="d",
            confidence=confidence,
            candidate_rank=1,
            hcc_number=hcc,
        )

    s_accept = suggestion(r1, "E11.22", "high", 37)
    s_reject = suggestion(r1, "I10", "medium", None)
    s_modify = suggestion(r2, "N18.31", "low", 329)
    suggestion(r3, "R60.0", "high", None)  # undecided

    def decide(s: Suggestion, action: str) -> None:
        ReviewDecision.objects.create(
            run=s.run,
            suggestion=s,
            reviewer=user,
            action=action,
            original_code=s.display_code,
        )

    # s_accept: first reject, then accept — the LATEST decision counts.
    decide(s_accept, "reject")
    decide(s_accept, "accept")
    decide(s_reject, "reject")
    decide(s_modify, "modify")

    audit_run = run(Run.Status.COMPLETED, duration=4000)
    for verdict in ("NOT_SUPPORTED", "INVALID_CODE", "MISSED_HCC"):
        AuditFinding.objects.create(
            run=audit_run, submitted_code="X", verdict=verdict, reason_code=verdict, reason="r"
        )

    for hit in (False, False, False, True):
        LlmCall.objects.create(
            step="extract",
            model_name="m",
            prompt_version="v1",
            request_hash="h",
            input_tokens=100,
            output_tokens=50,
            cache_hit=hit,
            status="ok",
        )
    return user


SINCE_DAYS = 30


def since() -> datetime:
    return services.window_start(SINCE_DAYS)


class TestMetrics:
    def test_notes_processed(self, seeded: User) -> None:
        # 2 ready_for_review + 2 completed (incl. the audit run)
        assert services.notes_processed(since()) == 4

    def test_failed_runs_by_error_code(self, seeded: User) -> None:
        assert services.failed_runs(since()) == {"LLM_RATE_LIMITED": 1}

    def test_average_processing_ms(self, seeded: User) -> None:
        # (1000 + 3000 + 2000 + 4000) / 4
        assert services.average_processing_ms(since()) == 2500

    def test_suggestions_made(self, seeded: User) -> None:
        assert services.suggestions_made(since()) == 4

    def test_acceptance_rate_uses_latest_decision(self, seeded: User) -> None:
        # 3 decided; latest actions: accept, reject, modify -> 1/3
        assert services.acceptance_rate(since()) == pytest.approx(1 / 3)

    def test_override_rate(self, seeded: User) -> None:
        # reject + modify = 2 of 3 decided
        assert services.override_rate(since()) == pytest.approx(2 / 3)

    def test_acceptance_by_confidence(self, seeded: User) -> None:
        rates = services.acceptance_rate_by_confidence(since())
        assert rates["high"] == 1.0  # the only decided High was accepted
        assert rates["medium"] == 0.0  # rejected
        assert rates["low"] == 0.0  # modified

    def test_hccs_captured(self, seeded: User) -> None:
        # accepted E11.22 (HCC 37) + modified N18.31 (HCC 329); I10 has none
        assert services.hccs_captured(since()) == 2

    def test_unsupported_codes_caught(self, seeded: User) -> None:
        assert services.unsupported_codes_caught(since()) == 2  # NOT_SUPPORTED + INVALID_CODE

    def test_missed_hccs_found(self, seeded: User) -> None:
        assert services.missed_hccs_found(since()) == 1

    def test_review_backlog(self, seeded: User) -> None:
        assert services.review_backlog() == 2

    def test_ai_usage(self, seeded: User) -> None:
        usage = services.ai_usage(since())
        assert usage.calls == 4
        assert usage.input_tokens == 400
        assert usage.output_tokens == 200
        assert usage.cache_hit_rate == pytest.approx(0.25)

    def test_runs_per_day(self, seeded: User) -> None:
        rows = services.runs_per_day(since())
        counts = [r["count"] for r in rows]
        assert all(isinstance(c, int) for c in counts)
        assert sum(c for c in counts if isinstance(c, int)) == 6

    def test_window_excludes_old_runs(self, seeded: User, user: User) -> None:
        note = Note.objects.first()
        assert note is not None
        old = Run.objects.create(
            note=note,
            mode="coding",
            created_by=user,
            status=Run.Status.COMPLETED,
        )
        Run.objects.filter(id=old.id).update(created_at=timezone.now() - timedelta(days=60))
        assert services.notes_processed(services.window_start(30)) == 4
        assert services.notes_processed(services.window_start(90)) == 5

    def test_empty_window_rates_are_none(self, db: None) -> None:
        assert services.acceptance_rate(since()) is None
        assert services.override_rate(since()) is None
        assert services.ai_usage(since()).cache_hit_rate is None


class TestDashboardEndpoint:
    def test_summary_shape(self, seeded: User, client: Client) -> None:
        body = client.get("/api/dashboard/summary?days=30").json()
        assert body["notes_processed"] == 4
        assert body["review_backlog"] == 2
        assert body["ai_usage"]["calls"] == 4
        assert body["acceptance_rate_by_confidence"]["high"] == 1.0

    def test_invalid_window_falls_back(self, seeded: User, client: Client) -> None:
        assert client.get("/api/dashboard/summary?days=12345").json()["days"] == 30
