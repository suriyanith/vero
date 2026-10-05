import csv
import uuid
from datetime import datetime
from typing import Any

from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse
from ninja import Router, Schema
from ninja.pagination import LimitOffsetPagination, paginate
from ninja.responses import Status

from apps.accounts.auth import current_user
from apps.review.models import ReviewDecision
from apps.review.services import (
    DecisionError,
    accept_all_high,
    record_decision,
    record_finding_decision,
)
from apps.runs.models import AuditFinding, Run, Suggestion

router = Router(tags=["review"])


class DecisionIn(Schema):
    action: ReviewDecision.Action
    final_code: str | None = None
    reason: str = ""


class DecisionOut(Schema):
    id: uuid.UUID
    action: str
    original_code: str
    final_code: str
    reason: str
    reviewer_name: str
    created_at: datetime


class AcceptHighOut(Schema):
    accepted: int
    decisions: list[DecisionOut]


class ErrorOut(Schema):
    error: dict[str, str]


def _decision_out(decision: ReviewDecision) -> DecisionOut:
    return DecisionOut(
        id=decision.id,
        action=decision.action,
        original_code=decision.original_code,
        final_code=decision.final_code,
        reason=decision.reason,
        reviewer_name=decision.reviewer.display_name or decision.reviewer.username,
        created_at=decision.created_at,
    )


@router.post(
    "/suggestions/{suggestion_id}/decisions",
    response={201: DecisionOut, 400: ErrorOut, 404: ErrorOut},
)
def create_decision(
    request: HttpRequest, suggestion_id: int, payload: DecisionIn
) -> Status[object]:
    suggestion = Suggestion.objects.select_related("run").filter(id=suggestion_id).first()
    if suggestion is None:
        return Status(
            404, {"error": {"code": "SUGGESTION_NOT_FOUND", "message": "Unknown suggestion."}}
        )
    try:
        decision = record_decision(
            suggestion,
            current_user(request),
            action=payload.action,
            final_code=payload.final_code,
            reason=payload.reason,
        )
    except DecisionError as exc:
        return Status(400, {"error": {"code": exc.code, "message": str(exc)}})
    return Status(201, _decision_out(decision))


@router.post("/runs/{run_id}/accept-high", response={200: AcceptHighOut, 404: ErrorOut})
def accept_high(request: HttpRequest, run_id: uuid.UUID) -> Status[object]:
    run = Run.objects.filter(id=run_id).first()
    if run is None:
        return Status(404, {"error": {"code": "RUN_NOT_FOUND", "message": "Unknown run."}})
    decisions = accept_all_high(run, current_user(request))
    return Status(
        200,
        AcceptHighOut(accepted=len(decisions), decisions=[_decision_out(d) for d in decisions]),
    )


@router.post(
    "/findings/{finding_id}/decisions",
    response={201: DecisionOut, 400: ErrorOut, 404: ErrorOut},
)
def create_finding_decision(
    request: HttpRequest, finding_id: int, payload: DecisionIn
) -> Status[object]:
    finding = AuditFinding.objects.select_related("run").filter(id=finding_id).first()
    if finding is None:
        return Status(404, {"error": {"code": "FINDING_NOT_FOUND", "message": "Unknown finding."}})
    try:
        decision = record_finding_decision(
            finding,
            current_user(request),
            action=payload.action,
            final_code=payload.final_code,
            reason=payload.reason,
        )
    except DecisionError as exc:
        return Status(400, {"error": {"code": exc.code, "message": str(exc)}})
    return Status(201, _decision_out(decision))


class DecisionListItemOut(Schema):
    id: uuid.UUID
    created_at: datetime
    reviewer_name: str
    action: str
    original_code: str
    final_code: str
    reason: str
    run_id: uuid.UUID
    run_mode: str
    note_title: str
    kind: str  # "suggestion" or "finding"


def _filtered_decisions(
    reviewer: str | None = None,
    action: str | None = None,
    code: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    run: uuid.UUID | None = None,
) -> "QuerySet[ReviewDecision]":
    decisions = ReviewDecision.objects.select_related("reviewer", "run", "run__note").order_by(
        "-created_at"
    )
    if reviewer:
        decisions = decisions.filter(reviewer__username=reviewer)
    if action:
        decisions = decisions.filter(action=action)
    if code:
        normalized = code.strip().upper()
        decisions = decisions.filter(
            Q(original_code__iexact=normalized) | Q(final_code__iexact=normalized)
        )
    if date_from:
        decisions = decisions.filter(created_at__gte=date_from)
    if date_to:
        decisions = decisions.filter(created_at__lte=date_to)
    if run:
        decisions = decisions.filter(run_id=run)
    return decisions


def _decision_list_item(d: ReviewDecision) -> DecisionListItemOut:
    return DecisionListItemOut(
        id=d.id,
        created_at=d.created_at,
        reviewer_name=d.reviewer.display_name or d.reviewer.username,
        action=d.action,
        original_code=d.original_code,
        final_code=d.final_code,
        reason=d.reason,
        run_id=d.run_id,
        run_mode=d.run.mode,
        note_title=d.run.note.title,
        kind="finding" if d.finding_id else "suggestion",
    )


@router.get("/decisions", response=list[DecisionListItemOut])
@paginate(LimitOffsetPagination)
def list_decisions(
    request: HttpRequest,
    reviewer: str | None = None,
    action: str | None = None,
    code: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    run: uuid.UUID | None = None,
    **params: Any,
) -> list[DecisionListItemOut]:
    decisions = _filtered_decisions(reviewer, action, code, date_from, date_to, run)
    return [_decision_list_item(d) for d in decisions]


DECISION_CSV_COLUMNS = [
    "decided_at",
    "reviewer",
    "action",
    "original_code",
    "final_code",
    "reason",
    "run_id",
    "run_mode",
    "note_title",
    "confidence_shown",
    "evidence_shown",
]


@router.get("/decisions/export.csv")
def export_decisions_csv(
    request: HttpRequest,
    reviewer: str | None = None,
    action: str | None = None,
    code: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    run: uuid.UUID | None = None,
) -> HttpResponse:
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="vero-decisions.csv"'
    writer = csv.writer(response)
    writer.writerow(DECISION_CSV_COLUMNS)
    for d in _filtered_decisions(reviewer, action, code, date_from, date_to, run):
        snapshot = d.evidence_snapshot or {}
        quotes = "; ".join(q.get("text", "") for q in snapshot.get("evidence", []))
        writer.writerow(
            [
                d.created_at.isoformat(),
                d.reviewer.display_name or d.reviewer.username,
                d.action,
                d.original_code,
                d.final_code,
                d.reason,
                str(d.run_id),
                d.run.mode,
                d.run.note.title,
                snapshot.get("confidence", snapshot.get("verdict", "")),
                quotes,
            ]
        )
    return response


@router.get("/runs/{run_id}/export.csv")
def export_run_csv(request: HttpRequest, run_id: uuid.UUID) -> HttpResponse:
    run = Run.objects.select_related("note").filter(id=run_id).first()
    if run is None:
        return HttpResponse(status=404)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="vero-run-{run_id}.csv"'
    writer = csv.writer(response)
    writer.writerow(
        [
            "kind",
            "code",
            "description_or_reason",
            "evidence",
            "meat",
            "hcc",
            "confidence_or_verdict",
            "decision",
            "final_code",
            "reviewer",
            "decided_at",
        ]
    )
    decisions_by_suggestion: dict[int, ReviewDecision] = {}
    decisions_by_finding: dict[int, ReviewDecision] = {}
    for d in run.decisions.select_related("reviewer").order_by("created_at"):
        if d.suggestion_id:
            decisions_by_suggestion[d.suggestion_id] = d  # latest wins
        if d.finding_id:
            decisions_by_finding[d.finding_id] = d
    for s in run.suggestions.all():
        sd = decisions_by_suggestion.get(s.id)
        writer.writerow(
            [
                "suggestion",
                s.display_code,
                s.description,
                "; ".join(q.get("text", "") for q in s.evidence),
                ", ".join(s.meat),
                s.hcc_number or "",
                s.confidence,
                sd.action if sd else "",
                sd.final_code if sd else "",
                (sd.reviewer.display_name or sd.reviewer.username) if sd else "",
                sd.created_at.isoformat() if sd else "",
            ]
        )
    for f in run.findings.all():
        fd = decisions_by_finding.get(f.id)
        writer.writerow(
            [
                "finding",
                f.submitted_code or f.suggested_code,
                f.reason,
                "; ".join(q.get("text", "") for q in f.evidence),
                "",
                "",
                f.verdict,
                fd.action if fd else "",
                fd.final_code if fd else "",
                (fd.reviewer.display_name or fd.reviewer.username) if fd else "",
                fd.created_at.isoformat() if fd else "",
            ]
        )
    return response
