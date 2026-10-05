"""Decision recording. Endpoints stay thin; the rules live here."""

from django.db import transaction
from django.db.models import Exists, OuterRef

from apps.accounts.models import User
from apps.reference.models import Icd10Code
from apps.review.models import ReviewDecision
from apps.runs.models import Run, Suggestion


class DecisionError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _snapshot(suggestion: Suggestion) -> dict[str, object]:
    """Freeze what the reviewer saw when they decided."""
    return {
        "display_code": suggestion.display_code,
        "description": suggestion.description,
        "evidence": suggestion.evidence,
        "meat": suggestion.meat,
        "confidence": suggestion.confidence,
        "confidence_reasons": suggestion.confidence_reasons,
        "rationale": suggestion.rationale,
        "flags": suggestion.flags,
        "hcc_number": suggestion.hcc_number,
        "hcc_label": suggestion.hcc_label,
    }


def _validate_final_code(run: Run, final_code: str) -> str:
    normalized = final_code.strip().upper()
    exists = Icd10Code.objects.filter(
        code_set=run.code_set, code=normalized.replace(".", ""), is_billable=True
    ).exists()
    if not exists:
        raise DecisionError(
            "INVALID_FINAL_CODE", f"{normalized} is not a billable code in the active code set."
        )
    return normalized


def _maybe_complete(run: Run) -> None:
    if run.status != Run.Status.READY_FOR_REVIEW:
        return
    undecided = (
        Suggestion.objects.filter(run=run)
        .annotate(decided=Exists(ReviewDecision.objects.filter(suggestion=OuterRef("pk"))))
        .filter(decided=False)
    )
    if not undecided.exists():
        run.status = Run.Status.COMPLETED
        run.save(update_fields=["status"])


@transaction.atomic
def record_decision(
    suggestion: Suggestion,
    reviewer: User,
    *,
    action: str,
    final_code: str | None = None,
    reason: str = "",
) -> ReviewDecision:
    run = suggestion.run
    if run.status not in (Run.Status.READY_FOR_REVIEW, Run.Status.COMPLETED):
        raise DecisionError("RUN_NOT_REVIEWABLE", "This run is not ready for review.")

    resolved_final = ""
    if action == ReviewDecision.Action.MODIFY:
        if not final_code:
            raise DecisionError("FINAL_CODE_REQUIRED", "Modify needs a replacement code.")
        resolved_final = _validate_final_code(run, final_code)
    elif action == ReviewDecision.Action.ACCEPT:
        resolved_final = suggestion.display_code

    decision = ReviewDecision.objects.create(
        run=run,
        suggestion=suggestion,
        reviewer=reviewer,
        action=action,
        original_code=suggestion.display_code,
        final_code=resolved_final,
        reason=reason,
        evidence_snapshot=_snapshot(suggestion),
    )
    _maybe_complete(run)
    return decision


@transaction.atomic
def accept_all_high(run: Run, reviewer: User) -> list[ReviewDecision]:
    """One accept decision per undecided High-confidence suggestion."""
    undecided_high = (
        Suggestion.objects.filter(run=run, confidence=Suggestion.Confidence.HIGH)
        .annotate(decided=Exists(ReviewDecision.objects.filter(suggestion=OuterRef("pk"))))
        .filter(decided=False)
    )
    decisions = [
        record_decision(suggestion, reviewer, action=ReviewDecision.Action.ACCEPT)
        for suggestion in undecided_high
    ]
    return decisions
