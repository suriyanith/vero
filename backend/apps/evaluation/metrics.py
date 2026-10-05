"""Evaluation metrics (Section 16.3). Pure functions over per-note results
so each one is unit-testable without the pipeline."""

from collections import Counter
from dataclasses import dataclass, field


def _dotless(code: str) -> str:
    return code.replace(".", "").upper()


def _category(code: str) -> str:
    return _dotless(code)[:3]


def precision_recall_f1(predicted: set[str], gold: set[str]) -> dict[str, float | None]:
    true_positives = len(predicted & gold)
    precision = true_positives / len(predicted) if predicted else None
    recall = true_positives / len(gold) if gold else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and (precision + recall) > 0
        else None
    )
    return {"precision": precision, "recall": recall, "f1": f1}


@dataclass
class CodingNoteResult:
    """What the pipeline produced for one note, next to its answer key."""

    note_title: str
    # (display_code, confidence, hcc_number or None)
    suggestions: list[tuple[str, str, int | None]]
    gold_codes: set[str]  # display codes
    gold_hccs: set[int]  # HCC numbers the gold codes map to
    # (condition_label, reason) that must NOT be coded
    gold_non_codes: list[tuple[str, str]]
    suggestion_condition_labels: list[str] = field(default_factory=list)
    dropped_quotes: int = 0
    unverified_quotes_shown: int = 0
    invalid_codes_shown: int = 0
    duration_ms: int = 0
    total_tokens: int = 0
    failed: bool = False


def _non_code_violated(condition_label: str, suggestion_labels: list[str]) -> bool:
    """Heuristic link between a do-not-code condition and a suggestion: the
    labels contain one another (documented in docs/DATASET_CARD.md)."""
    needle = condition_label.lower()
    return any(needle in label.lower() or label.lower() in needle for label in suggestion_labels)


def coding_metrics(results: list[CodingNoteResult]) -> dict[str, object]:
    predicted_all: set[tuple[str, str]] = set()
    gold_all: set[tuple[str, str]] = set()
    predicted_hccs: set[tuple[str, int]] = set()
    gold_hccs: set[tuple[str, int]] = set()
    predicted_categories: set[tuple[str, str]] = set()
    gold_categories: set[tuple[str, str]] = set()

    confidence_counts: Counter[str] = Counter()
    confidence_correct: Counter[str] = Counter()
    hard_case_total: Counter[str] = Counter()
    hard_case_correct: Counter[str] = Counter()

    for result in results:
        note = result.note_title
        predicted_codes = {_dotless(code) for code, _, _ in result.suggestions}
        gold_codes = {_dotless(code) for code in result.gold_codes}
        predicted_all |= {(note, code) for code in predicted_codes}
        gold_all |= {(note, code) for code in gold_codes}
        predicted_hccs |= {(note, hcc) for _, _, hcc in result.suggestions if hcc is not None}
        gold_hccs |= {(note, hcc) for hcc in result.gold_hccs}
        predicted_categories |= {(note, code[:3]) for code in predicted_codes}
        gold_categories |= {(note, code[:3]) for code in gold_codes}

        for code, confidence, _ in result.suggestions:
            confidence_counts[confidence] += 1
            if _dotless(code) in gold_codes:
                confidence_correct[confidence] += 1

        for label, reason in result.gold_non_codes:
            hard_case_total[reason] += 1
            if not _non_code_violated(label, result.suggestion_condition_labels):
                hard_case_correct[reason] += 1

    return {
        "code_level": precision_recall_f1(
            {f"{n}:{c}" for n, c in predicted_all}, {f"{n}:{c}" for n, c in gold_all}
        ),
        "hcc_level": precision_recall_f1(
            {f"{n}:{h}" for n, h in predicted_hccs}, {f"{n}:{h}" for n, h in gold_hccs}
        ),
        "category_level": precision_recall_f1(
            {f"{n}:{c}" for n, c in predicted_categories},
            {f"{n}:{c}" for n, c in gold_categories},
        ),
        "accuracy_by_confidence": {
            level: (confidence_correct[level] / confidence_counts[level])
            if confidence_counts[level]
            else None
            for level in ("high", "medium", "low")
        },
        "hard_cases": {
            reason: {
                "total": hard_case_total[reason],
                "correctly_not_coded": hard_case_correct[reason],
                "accuracy": hard_case_correct[reason] / hard_case_total[reason],
            }
            for reason in sorted(hard_case_total)
        },
        "evidence_integrity": {
            "dropped_quotes": sum(r.dropped_quotes for r in results),
            "unverified_quotes_shown": sum(r.unverified_quotes_shown for r in results),
            "invalid_codes_shown": sum(r.invalid_codes_shown for r in results),
        },
    }


UNSUPPORTED = {"NOT_SUPPORTED", "WEAK_SUPPORT", "INVALID_CODE"}


@dataclass
class AuditCaseResult:
    note_title: str
    # {display_code: (expected_verdict, actual_verdict)}
    verdicts: dict[str, tuple[str, str]]


def audit_metrics(results: list[AuditCaseResult]) -> dict[str, object]:
    per_verdict_total: Counter[str] = Counter()
    per_verdict_correct: Counter[str] = Counter()
    confusion: Counter[str] = Counter()
    unsupported_total = unsupported_caught = 0
    supported_total = supported_wrongly_flagged = 0

    for result in results:
        for expected, actual in result.verdicts.values():
            per_verdict_total[expected] += 1
            confusion[f"{expected}->{actual}"] += 1
            if expected == actual:
                per_verdict_correct[expected] += 1
            if expected in UNSUPPORTED:
                unsupported_total += 1
                if actual in UNSUPPORTED:
                    unsupported_caught += 1
            if expected == "SUPPORTED":
                supported_total += 1
                if actual != "SUPPORTED":
                    supported_wrongly_flagged += 1

    total = sum(per_verdict_total.values())
    correct = sum(per_verdict_correct.values())
    return {
        "overall_accuracy": correct / total if total else None,
        "per_verdict_accuracy": {
            verdict: per_verdict_correct[verdict] / per_verdict_total[verdict]
            for verdict in sorted(per_verdict_total)
        },
        "confusion": dict(sorted(confusion.items())),
        "unsupported_caught_rate": (
            unsupported_caught / unsupported_total if unsupported_total else None
        ),
        "supported_wrongly_flagged_rate": (
            supported_wrongly_flagged / supported_total if supported_total else None
        ),
    }


def operational_metrics(results: list[CodingNoteResult]) -> dict[str, object]:
    attempted = len(results)
    succeeded = [r for r in results if not r.failed]
    durations = [r.duration_ms for r in succeeded]
    tokens = [r.total_tokens for r in succeeded]
    return {
        "notes_attempted": attempted,
        "success_rate": len(succeeded) / attempted if attempted else None,
        "average_duration_ms": round(sum(durations) / len(durations)) if durations else None,
        "slowest_duration_ms": max(durations) if durations else None,
        "average_tokens": round(sum(tokens) / len(tokens)) if tokens else None,
    }
