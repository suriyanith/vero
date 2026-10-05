import uuid
from datetime import datetime
from typing import Any

from django.db.models import Count, QuerySet
from django.http import HttpRequest
from ninja import File, Form, Router, Schema, UploadedFile
from ninja.pagination import LimitOffsetPagination, paginate
from ninja.responses import Status

from apps.accounts.auth import current_user
from apps.notes.models import Mode, Note
from apps.runs.models import Run
from apps.runs.services import RunCreationError, create_batch, create_run, retry_run

router = Router(tags=["runs"])


# ---------- schemas ----------
class SampleOut(Schema):
    id: uuid.UUID
    title: str
    preview: str


class RunCreateIn(Schema):
    text: str | None = None
    sample_id: uuid.UUID | None = None
    mode: Mode = Mode.CODING
    submitted_codes: list[str] = []


class RunCreatedOut(Schema):
    run_id: uuid.UUID


class RejectedFileOut(Schema):
    filename: str
    code: str
    reason: str


class BatchCreatedOut(Schema):
    batch_id: uuid.UUID
    run_ids: list[uuid.UUID]
    rejected: list[RejectedFileOut]


class RunListItemOut(Schema):
    id: uuid.UUID
    status: str
    mode: str
    note_title: str
    created_by_name: str
    created_at: datetime
    suggestion_count: int
    error_code: str

    @staticmethod
    def resolve_note_title(obj: Run) -> str:
        return obj.note.title

    @staticmethod
    def resolve_created_by_name(obj: Run) -> str:
        return obj.created_by.display_name or obj.created_by.username

    @staticmethod
    def resolve_suggestion_count(obj: Run) -> int:
        return getattr(obj, "suggestion_count", 0)


class QuoteOut(Schema):
    text: str
    start: int
    end: int
    meat: list[str]
    match_type: str
    ambiguous: bool


class ConditionOut(Schema):
    id: int
    label: str
    status: str
    specificity_details: list[str]
    quotes: list[QuoteOut]


class SuggestionOut(Schema):
    id: int
    condition_id: int | None
    display_code: str
    description: str
    hcc_number: int | None
    hcc_label: str
    evidence: list[QuoteOut]
    meat: list[str]
    confidence: str
    confidence_reasons: list[str]
    rationale: str
    flags: list[str]
    candidate_rank: int


class NoteOut(Schema):
    id: uuid.UUID
    title: str
    text: str


class RunDetailOut(Schema):
    id: uuid.UUID
    status: str
    mode: str
    note: NoteOut
    conditions: list[ConditionOut]
    suggestions: list[SuggestionOut]
    submitted_codes: list[str]
    model_name: str
    prompt_versions: dict[str, str]
    duration_ms: int | None
    input_tokens: int
    output_tokens: int
    dropped_quotes: int
    error_code: str
    error_message: str
    created_at: datetime


class ErrorOut(Schema):
    error: dict[str, str]


# ---------- endpoints ----------
@router.get("/samples", response=list[SampleOut])
def list_samples(request: HttpRequest) -> list[SampleOut]:
    return [
        SampleOut(id=note.id, title=note.title, preview=note.text[:200])
        for note in Note.objects.filter(source=Note.Source.SAMPLE).order_by("title")
    ]


@router.post("/runs", response={202: RunCreatedOut, 400: ErrorOut})
def create_run_view(request: HttpRequest, payload: RunCreateIn) -> Status[object]:
    try:
        run = create_run(
            current_user(request),
            text=payload.text,
            sample_id=str(payload.sample_id) if payload.sample_id else None,
            mode=payload.mode,
            submitted_codes=payload.submitted_codes,
        )
    except RunCreationError as exc:
        return Status(400, {"error": {"code": exc.code, "message": str(exc)}})
    return Status(202, RunCreatedOut(run_id=run.id))


@router.post("/batches", response={202: BatchCreatedOut, 400: ErrorOut})
def create_batch_view(
    request: HttpRequest,
    mode: Form[Mode],
    files: File[list[UploadedFile]],
) -> Status[object]:
    decoded: list[tuple[str, str]] = []
    rejected_early: list[RejectedFileOut] = []
    for uploaded in files:
        name = uploaded.name or "unnamed"
        if not name.lower().endswith(".txt"):
            rejected_early.append(
                RejectedFileOut(
                    filename=name, code="NOT_TXT", reason="Only .txt files are accepted."
                )
            )
            continue
        try:
            decoded.append((name, uploaded.read().decode("utf-8")))
        except UnicodeDecodeError:
            rejected_early.append(
                RejectedFileOut(
                    filename=name, code="NOT_UTF8", reason="The file is not valid UTF-8 text."
                )
            )

    try:
        batch, runs, rejected = create_batch(
            current_user(request),
            name=f"Batch of {len(files)} file(s)",
            files=decoded,
            mode=mode,
        )
    except RunCreationError as exc:
        return Status(400, {"error": {"code": exc.code, "message": str(exc)}})
    return Status(
        202,
        BatchCreatedOut(
            batch_id=batch.id,
            run_ids=[run.id for run in runs],
            rejected=rejected_early
            + [
                RejectedFileOut(filename=r.filename, code=r.code, reason=r.reason) for r in rejected
            ],
        ),
    )


@router.get("/runs", response=list[RunListItemOut])
@paginate(LimitOffsetPagination)
def list_runs(
    request: HttpRequest,
    status: str | None = None,
    mode: str | None = None,
    batch: uuid.UUID | None = None,
    mine: bool = False,
    **params: Any,
) -> QuerySet[Run]:
    runs = (
        Run.objects.select_related("note", "created_by")
        .annotate(suggestion_count=Count("suggestions"))
        .order_by("-created_at")
    )
    if status:
        runs = runs.filter(status=status)
    if mode:
        runs = runs.filter(mode=mode)
    if batch:
        runs = runs.filter(note__batch_id=batch)
    if mine:
        runs = runs.filter(created_by=current_user(request))
    return runs


@router.get("/runs/{run_id}", response={200: RunDetailOut, 404: ErrorOut})
def get_run(request: HttpRequest, run_id: uuid.UUID) -> Status[object]:
    run = (
        Run.objects.select_related("note")
        .prefetch_related("conditions", "suggestions")
        .filter(id=run_id)
        .first()
    )
    if run is None:
        return Status(404, {"error": {"code": "RUN_NOT_FOUND", "message": "Unknown run."}})
    return Status(
        200,
        RunDetailOut(
            id=run.id,
            status=run.status,
            mode=run.mode,
            note=NoteOut(id=run.note.id, title=run.note.title, text=run.note.text),
            conditions=[
                ConditionOut(
                    id=c.id,
                    label=c.label,
                    status=c.status,
                    specificity_details=c.specificity_details,
                    quotes=c.quotes,
                )
                for c in run.conditions.all()
            ],
            suggestions=[
                SuggestionOut(
                    id=s.id,
                    condition_id=s.condition_id,
                    display_code=s.display_code,
                    description=s.description,
                    hcc_number=s.hcc_number,
                    hcc_label=s.hcc_label,
                    evidence=s.evidence,
                    meat=s.meat,
                    confidence=s.confidence,
                    confidence_reasons=s.confidence_reasons,
                    rationale=s.rationale,
                    flags=s.flags,
                    candidate_rank=s.candidate_rank,
                )
                for s in run.suggestions.all()
            ],
            submitted_codes=run.submitted_codes,
            model_name=run.model_name,
            prompt_versions=run.prompt_versions,
            duration_ms=run.duration_ms,
            input_tokens=run.input_tokens,
            output_tokens=run.output_tokens,
            dropped_quotes=run.dropped_quotes,
            error_code=run.error_code,
            error_message=run.error_message,
            created_at=run.created_at,
        ),
    )


@router.post("/runs/{run_id}/retry", response={202: RunCreatedOut, 400: ErrorOut, 404: ErrorOut})
def retry_run_view(request: HttpRequest, run_id: uuid.UUID) -> Status[object]:
    run = Run.objects.filter(id=run_id).first()
    if run is None:
        return Status(404, {"error": {"code": "RUN_NOT_FOUND", "message": "Unknown run."}})
    try:
        new_run = retry_run(run, current_user(request))
    except RunCreationError as exc:
        return Status(400, {"error": {"code": exc.code, "message": str(exc)}})
    return Status(202, RunCreatedOut(run_id=new_run.id))
