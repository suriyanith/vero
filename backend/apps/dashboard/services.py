"""Dashboard metrics (Section 17 of the plan). Each function is tested
against hand-computed values on seeded data.

"Decided" means a suggestion has at least one decision; the current decision
is the latest one. Windows are over run/decision/finding creation time.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from django.db.models import Avg, Count, OuterRef, Subquery, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.llm.models import LlmCall
from apps.review.models import ReviewDecision
from apps.runs.models import AuditFinding, Run, Suggestion

SUCCESSFUL_STATUSES = (Run.Status.READY_FOR_REVIEW, Run.Status.COMPLETED)
UNSUPPORTED_VERDICTS = ("NOT_SUPPORTED", "WEAK_SUPPORT", "INVALID_CODE")


def window_start(days: int) -> datetime:
    return timezone.now() - timedelta(days=days)


def notes_processed(since: datetime) -> int:
    return Run.objects.filter(created_at__gte=since, status__in=SUCCESSFUL_STATUSES).count()


def failed_runs(since: datetime) -> dict[str, int]:
    rows = (
        Run.objects.filter(created_at__gte=since, status=Run.Status.FAILED)
        .values("error_code")
        .annotate(count=Count("id"))
    )
    return {row["error_code"] or "UNKNOWN": row["count"] for row in rows}


def average_processing_ms(since: datetime) -> int | None:
    value = Run.objects.filter(created_at__gte=since, status__in=SUCCESSFUL_STATUSES).aggregate(
        avg=Avg("duration_ms")
    )["avg"]
    return round(value) if value is not None else None


def suggestions_made(since: datetime) -> int:
    return Suggestion.objects.filter(run__created_at__gte=since).count()


# Returns Suggestion rows annotated with latest_action; typed Any because
# django-stubs loses annotation fields behind an explicit QuerySet type.
def _suggestions_with_latest_action(since: datetime) -> Any:
    latest = (
        ReviewDecision.objects.filter(suggestion=OuterRef("pk"))
        .order_by("-created_at")
        .values("action")[:1]
    )
    return (
        Suggestion.objects.filter(run__created_at__gte=since)
        .annotate(latest_action=Subquery(latest))
        .filter(latest_action__isnull=False)
    )


def acceptance_rate(since: datetime) -> float | None:
    decided = _suggestions_with_latest_action(since)
    total: int = decided.count()
    if total == 0:
        return None
    accepted: int = decided.filter(latest_action=ReviewDecision.Action.ACCEPT).count()
    return accepted / total


def override_rate(since: datetime) -> float | None:
    decided = _suggestions_with_latest_action(since)
    total: int = decided.count()
    if total == 0:
        return None
    overridden: int = decided.filter(
        latest_action__in=[ReviewDecision.Action.MODIFY, ReviewDecision.Action.REJECT]
    ).count()
    return overridden / total


def acceptance_rate_by_confidence(since: datetime) -> dict[str, float | None]:
    """The live check on whether confidence levels mean something."""
    decided = _suggestions_with_latest_action(since)
    rates: dict[str, float | None] = {}
    for level in Suggestion.Confidence.values:
        subset = decided.filter(confidence=level)
        total = subset.count()
        rates[level] = (
            subset.filter(latest_action=ReviewDecision.Action.ACCEPT).count() / total
            if total
            else None
        )
    return rates


def hccs_captured(since: datetime) -> int:
    count: int = (
        _suggestions_with_latest_action(since)
        .filter(
            latest_action__in=[ReviewDecision.Action.ACCEPT, ReviewDecision.Action.MODIFY],
            hcc_number__isnull=False,
        )
        .count()
    )
    return count


def unsupported_codes_caught(since: datetime) -> int:
    return AuditFinding.objects.filter(
        run__created_at__gte=since, verdict__in=UNSUPPORTED_VERDICTS
    ).count()


def missed_hccs_found(since: datetime) -> int:
    return AuditFinding.objects.filter(
        run__created_at__gte=since, verdict=AuditFinding.Verdict.MISSED_HCC
    ).count()


def review_backlog() -> int:
    """Current backlog — not windowed."""
    return Run.objects.filter(status=Run.Status.READY_FOR_REVIEW).count()


@dataclass(frozen=True)
class AiUsage:
    calls: int
    input_tokens: int
    output_tokens: int
    cache_hit_rate: float | None


def ai_usage(since: datetime) -> AiUsage:
    calls = LlmCall.objects.filter(created_at__gte=since)
    total = calls.count()
    sums = calls.aggregate(input=Sum("input_tokens"), output=Sum("output_tokens"))
    hits = calls.filter(cache_hit=True).count()
    return AiUsage(
        calls=total,
        input_tokens=sums["input"] or 0,
        output_tokens=sums["output"] or 0,
        cache_hit_rate=hits / total if total else None,
    )


def runs_per_day(since: datetime) -> list[dict[str, object]]:
    rows = (
        Run.objects.filter(created_at__gte=since)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    return [{"day": row["day"].isoformat(), "count": row["count"]} for row in rows]


def summary(days: int) -> dict[str, object]:
    since = window_start(days)
    usage = ai_usage(since)
    return {
        "days": days,
        "notes_processed": notes_processed(since),
        "failed_runs": failed_runs(since),
        "average_processing_ms": average_processing_ms(since),
        "suggestions_made": suggestions_made(since),
        "acceptance_rate": acceptance_rate(since),
        "override_rate": override_rate(since),
        "acceptance_rate_by_confidence": acceptance_rate_by_confidence(since),
        "hccs_captured": hccs_captured(since),
        "unsupported_codes_caught": unsupported_codes_caught(since),
        "missed_hccs_found": missed_hccs_found(since),
        "review_backlog": review_backlog(),
        "ai_usage": {
            "calls": usage.calls,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cache_hit_rate": usage.cache_hit_rate,
        },
        "runs_per_day": runs_per_day(since),
    }
