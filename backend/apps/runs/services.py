"""Run creation and result persistence. Endpoints stay thin; logic lives here."""

import hashlib
import re
from dataclasses import dataclass

from django.conf import settings
from django.db import transaction

from apps.accounts.models import User
from apps.notes.models import Batch, Mode, Note
from apps.notes.phi import find_phi
from apps.reference.services import active_code_set, active_hcc_model
from apps.runs.models import AuditFinding, Condition, Run, Suggestion
from vero_core.schemas import AuditResult, CodingResult

DISPLAY_CODE_RE = re.compile(r"^[A-TV-Z][0-9][0-9A-Z](?:\.[0-9A-Z]{1,4})?$")

PIPELINE_VERSION = "1"


class RunCreationError(Exception):
    """Input was rejected; `code` is the stable user-facing error code."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _validate_note_text(text: str) -> None:
    if not text.strip():
        raise RunCreationError("INPUT_EMPTY", "The note is empty.")
    if len(text) > settings.VERO_MAX_NOTE_CHARS:
        raise RunCreationError(
            "INPUT_TOO_LARGE",
            f"The note exceeds {settings.VERO_MAX_NOTE_CHARS} characters.",
        )
    found = find_phi(text)
    if found:
        raise RunCreationError(
            "PHI_DETECTED",
            "The note looks like it contains real patient identifiers "
            f"({', '.join(found)}). Vero accepts synthetic notes only.",
        )


def _validate_mode(mode: str, submitted_codes: list[str]) -> None:
    if mode == Mode.AUDIT:
        # The audit pipeline arrives in Phase 5; validate shape now anyway.
        if not submitted_codes:
            raise RunCreationError(
                "SUBMITTED_CODES_REQUIRED", "Audit mode needs at least one submitted code."
            )
        bad = [c for c in submitted_codes if not DISPLAY_CODE_RE.match(c.upper())]
        if bad:
            raise RunCreationError(
                "INVALID_CODE_FORMAT",
                f"Not valid ICD-10-CM code formats: {', '.join(bad)}",
            )


def _enqueue(run: Run) -> None:
    from apps.runs.tasks import process_run

    # The worker must never see an uncommitted run.
    transaction.on_commit(lambda: process_run.enqueue(str(run.id)))


def _new_run(note: Note, mode: str, submitted_codes: list[str], user: User) -> Run:
    run = Run.objects.create(
        note=note,
        mode=mode,
        submitted_codes=[c.upper() for c in submitted_codes],
        pipeline_version=PIPELINE_VERSION,
        code_set=active_code_set(),
        hcc_model=active_hcc_model(),
        created_by=user,
    )
    _enqueue(run)
    return run


@transaction.atomic
def create_run(
    user: User,
    *,
    text: str | None = None,
    sample_id: str | None = None,
    mode: str = Mode.CODING,
    submitted_codes: list[str] | None = None,
) -> Run:
    submitted_codes = submitted_codes or []
    _validate_mode(mode, submitted_codes)

    if sample_id is not None:
        note = Note.objects.filter(id=sample_id, source=Note.Source.SAMPLE).first()
        if note is None:
            raise RunCreationError("SAMPLE_NOT_FOUND", "Unknown sample note.")
    elif text is not None:
        _validate_note_text(text)
        note = Note.objects.create(
            title=text.strip().splitlines()[0][:80],
            text=text,
            text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            source=Note.Source.USER,
            created_by=user,
        )
    else:
        raise RunCreationError("INPUT_EMPTY", "Provide either note text or a sample id.")

    return _new_run(note, mode, submitted_codes, user)


@dataclass(frozen=True)
class RejectedFile:
    filename: str
    code: str
    reason: str


@transaction.atomic
def create_batch(
    user: User, *, name: str, files: list[tuple[str, str]], mode: str = Mode.CODING
) -> tuple[Batch, list[Run], list[RejectedFile]]:
    """Files are (filename, text) pairs, already decoded; one note+run each."""
    if len(files) > settings.VERO_MAX_BATCH_FILES:
        raise RunCreationError(
            "TOO_MANY_FILES", f"A batch accepts at most {settings.VERO_MAX_BATCH_FILES} files."
        )
    if mode == Mode.AUDIT:
        # Batch uploads are coding-only: audit needs per-note submitted codes.
        raise RunCreationError("BATCH_AUDIT_UNSUPPORTED", "Batches run in coding mode only.")

    batch = Batch.objects.create(name=name, mode=mode, created_by=user)
    runs: list[Run] = []
    rejected: list[RejectedFile] = []
    for filename, text in files:
        try:
            _validate_note_text(text)
        except RunCreationError as exc:
            rejected.append(RejectedFile(filename=filename, code=exc.code, reason=str(exc)))
            continue
        note = Note.objects.create(
            title=filename,
            text=text,
            text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            source=Note.Source.USER,
            batch=batch,
            created_by=user,
        )
        runs.append(_new_run(note, mode, [], user))
    return batch, runs, rejected


def save_coding_result(run: Run, result: CodingResult) -> None:
    """Persist a pipeline result; the caller wraps this in the run transaction."""
    conditions_by_label: dict[str, Condition] = {}
    for condition in result.conditions:
        row = Condition.objects.create(
            run=run,
            label=condition.label,
            status=condition.status.value,
            specificity_details=condition.specificity_details,
            quotes=[q.model_dump(mode="json") for q in condition.quotes],
        )
        conditions_by_label.setdefault(condition.label, row)

    for suggestion in result.suggestions:
        # A merged suggestion's label is "a + b"; link the first condition.
        first_label = suggestion.condition_label.split(" + ")[0]
        Suggestion.objects.create(
            run=run,
            condition=conditions_by_label.get(first_label),
            display_code=suggestion.code,
            description=suggestion.description,
            hcc_number=suggestion.hcc_number,
            hcc_label=suggestion.hcc_label or "",
            evidence=[q.model_dump(mode="json") for q in suggestion.evidence],
            meat=[m.value for m in suggestion.meat],
            confidence=suggestion.confidence.value,
            confidence_reasons=suggestion.confidence_reasons,
            rationale=suggestion.rationale,
            flags=suggestion.flags,
            candidate_rank=suggestion.candidate_rank,
        )


@transaction.atomic
def retry_run(run: Run, user: User) -> Run:
    if run.status != Run.Status.FAILED:
        raise RunCreationError("NOT_RETRYABLE", "Only failed runs can be retried.")
    new_run = Run.objects.create(
        note=run.note,
        mode=run.mode,
        submitted_codes=run.submitted_codes,
        retry_of=run,
        pipeline_version=PIPELINE_VERSION,
        code_set=active_code_set(),
        hcc_model=active_hcc_model(),
        created_by=user,
    )
    _enqueue(new_run)
    return new_run


def save_audit_result(run: Run, result: AuditResult) -> None:
    """Persist the audit findings on top of the underlying coding result."""
    save_coding_result(run, result.coding)
    for finding in result.findings:
        AuditFinding.objects.create(
            run=run,
            submitted_code=finding.submitted_code or "",
            verdict=finding.verdict.value,
            reason_code=finding.reason_code,
            reason=finding.reason,
            evidence=[q.model_dump(mode="json") for q in finding.evidence],
            suggested_code=finding.suggested_code or "",
        )
