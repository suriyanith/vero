import uuid
from datetime import datetime

from django.http import HttpRequest
from ninja import Router, Schema
from ninja.responses import Status

from apps.accounts.auth import current_user
from apps.review.models import ReviewDecision
from apps.review.services import DecisionError, accept_all_high, record_decision
from apps.runs.models import Run, Suggestion

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
