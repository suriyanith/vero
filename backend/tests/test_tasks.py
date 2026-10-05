from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import User
from apps.notes.models import Note
from apps.runs.models import Run
from apps.runs.tasks import process_run
from tests.test_loaders import load_fixture_code_set
from vero_core.errors import LLM_RATE_LIMITED, LLMError


@pytest.fixture
def run(user: User) -> Run:
    note = Note.objects.create(
        title="t", text="some note", text_sha256="x", source=Note.Source.USER, created_by=user
    )
    return Run.objects.create(note=note, mode="coding", created_by=user)


@pytest.mark.django_db
class TestProcessRun:
    def test_noop_when_not_queued(self, run: Run) -> None:
        Run.objects.filter(id=run.id).update(status=Run.Status.READY_FOR_REVIEW)
        process_run.func(str(run.id))
        run.refresh_from_db()
        assert run.status == Run.Status.READY_FOR_REVIEW  # untouched

    def test_llm_error_fails_run_with_stable_code(
        self, run: Run, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        load_fixture_code_set()

        def broken_client(run_id: object = None) -> object:
            raise LLMError(LLM_RATE_LIMITED, "quota exhausted")

        monkeypatch.setattr("apps.runs.tasks.build_llm_client", broken_client)
        process_run.func(str(run.id))
        run.refresh_from_db()
        assert run.status == Run.Status.FAILED
        assert run.error_code == LLM_RATE_LIMITED
        assert "Traceback" not in run.error_message

    def test_unexpected_error_fails_safely(self, run: Run, monkeypatch: pytest.MonkeyPatch) -> None:
        def exploding_client(run_id: object = None) -> object:
            raise RuntimeError("secret internals leaked here")

        monkeypatch.setattr("apps.runs.tasks.build_llm_client", exploding_client)
        load_fixture_code_set()
        process_run.func(str(run.id))
        run.refresh_from_db()
        assert run.status == Run.Status.FAILED
        assert run.error_code == "INTERNAL"
        assert "secret internals" not in run.error_message


@pytest.mark.django_db
class TestFailStuckRuns:
    def test_marks_only_old_processing_runs(self, run: Run, user: User) -> None:
        old = timezone.now() - timedelta(minutes=30)
        Run.objects.filter(id=run.id).update(status=Run.Status.PROCESSING, started_at=old)
        fresh = Run.objects.create(
            note=run.note,
            mode="coding",
            created_by=user,
            status=Run.Status.PROCESSING,
            started_at=timezone.now(),
        )
        call_command("fail_stuck_runs", older_than=15)
        run.refresh_from_db()
        fresh.refresh_from_db()
        assert run.status == Run.Status.FAILED
        assert run.error_code == "WORKER_TIMEOUT"
        assert fresh.status == Run.Status.PROCESSING
