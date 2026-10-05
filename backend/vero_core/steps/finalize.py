"""Step 5 — Finalize (Python): validate, deduplicate, reconcile, map HCC,
and assign rule-based confidence."""

import re
from dataclasses import dataclass

from vero_core.interfaces import PipelineConfig
from vero_core.schemas import (
    Candidate,
    Certainty,
    ConditionSelection,
    Confidence,
    DroppedItem,
    Suggestion,
    VerifiedCondition,
    VerifiedQuote,
)

FLAG_EXCLUDES1 = "excludes1_conflict"
FLAG_MISSING_ADDITIONAL = "missing_additional_code"
FLAG_UNDERSPECIFIED = "possibly_underspecified"
FLAG_NO_MEAT = "no_meat"

_CODE_REF_RE = re.compile(r"\b[A-TV-Z][0-9][0-9A-Z](?:\.[0-9A-Z]{1,4})?")


@dataclass
class _Draft:
    """A suggestion being assembled; becomes a Suggestion once rules run."""

    candidate: Candidate
    condition_labels: list[str]
    evidence: list[VerifiedQuote]
    rationales: list[str]
    certainty: Certainty
    specificity_flags: list[str]
    candidate_rank: int


def _codes_match(display_code: str, ref: str) -> bool:
    """Dotless prefix match: ref "E10" covers E10.22; "N18.3" covers N18.31."""
    return display_code.replace(".", "").startswith(ref.replace(".", ""))


def _worst_certainty(a: Certainty, b: Certainty) -> Certainty:
    order = [Certainty.LOW, Certainty.MEDIUM, Certainty.HIGH]
    return min(a, b, key=order.index)


def _build_drafts(
    conditions: list[VerifiedCondition],
    selections: dict[int, ConditionSelection],
    candidates: list[list[Candidate]],
) -> tuple[dict[str, _Draft], list[DroppedItem]]:
    drafts: dict[str, _Draft] = {}
    dropped: list[DroppedItem] = []

    for index, condition in enumerate(conditions, start=1):
        selection = selections.get(index)
        if selection is None:
            dropped.append(DroppedItem(label=condition.label, reason="no_selection"))
            continue
        if selection.no_fit or not selection.codes:
            dropped.append(DroppedItem(label=condition.label, reason="no_fit"))
            continue
        by_display = {c.display_code: c for c in candidates[index - 1]}
        for choice in selection.codes:
            candidate = by_display[choice.code]
            if not candidate.is_billable:
                dropped.append(DroppedItem(label=condition.label, reason="invalid_code"))
                continue
            existing = drafts.get(choice.code)
            if existing is None:
                drafts[choice.code] = _Draft(
                    candidate=candidate,
                    condition_labels=[condition.label],
                    evidence=list(condition.quotes),
                    rationales=[choice.rationale],
                    certainty=selection.certainty,
                    specificity_flags=list(selection.specificity_flags),
                    candidate_rank=candidate.rank,
                )
            else:
                # Two conditions chose the same code: merge into one suggestion.
                if condition.label not in existing.condition_labels:
                    existing.condition_labels.append(condition.label)
                seen_spans = {(q.start, q.end) for q in existing.evidence}
                existing.evidence.extend(
                    q for q in condition.quotes if (q.start, q.end) not in seen_spans
                )
                existing.rationales.append(choice.rationale)
                existing.certainty = _worst_certainty(existing.certainty, selection.certainty)
                existing.specificity_flags.extend(
                    f for f in selection.specificity_flags if f not in existing.specificity_flags
                )
                existing.candidate_rank = min(existing.candidate_rank, candidate.rank)
    return drafts, dropped


def _reconcile_flags(draft: _Draft, all_drafts: dict[str, _Draft]) -> list[str]:
    flags: list[str] = []
    notes = draft.candidate.notes

    for ref in notes.get("excludes1_codes", []):
        if any(
            other != draft.candidate.display_code and _codes_match(other, ref)
            for other in all_drafts
        ):
            flags.append(FLAG_EXCLUDES1)
            break

    # "Use additional code" notes that point at disease-code families (not
    # Z status codes, which are conditional in practice and out of v1 scope):
    # flag when no other suggested code satisfies the note. Satisfaction is
    # category-level because notes often cite ranges ("N18.1-N18.6") whose
    # endpoints are not prefixes of the member codes (N18.31).
    for note in notes.get("use_additional", []):
        categories = {
            ref.replace(".", "")[:3]
            for ref in _CODE_REF_RE.findall(note)
            if not ref.startswith("Z")
        }
        if categories and not any(
            other.replace(".", "")[:3] in categories
            for other in all_drafts
            if other != draft.candidate.display_code
        ):
            flags.append(FLAG_MISSING_ADDITIONAL)
            break

    return flags


def _confidence(
    draft: _Draft, flags: list[str], config: PipelineConfig
) -> tuple[Confidence, list[str]]:
    """Simple, explainable rules; every applied reason is recorded."""
    low_triggers = []
    if FLAG_NO_MEAT in flags:
        low_triggers.append("no MEAT element in any evidence quote")
    if FLAG_EXCLUDES1 in flags:
        low_triggers.append("Excludes1 conflict with another suggested code")
    if draft.certainty == Certainty.LOW:
        low_triggers.append("model certainty was low")
    if draft.candidate_rank >= config.low_confidence_min_rank:
        low_triggers.append(f"candidate rank {draft.candidate_rank} is outside the top 10")
    if low_triggers:
        return Confidence.LOW, low_triggers

    failed_high = []
    if not all(q.match_type == "exact" and not q.ambiguous for q in draft.evidence):
        failed_high.append("evidence matched case-insensitively or ambiguously")
    if not any(q.meat for q in draft.evidence):
        failed_high.append("no MEAT element")  # unreachable while no_meat is a Low trigger
    if draft.candidate_rank > config.high_confidence_max_rank:
        failed_high.append(f"candidate rank {draft.candidate_rank} is outside the top 3")
    if draft.certainty != Certainty.HIGH:
        failed_high.append(f"model certainty was {draft.certainty.value}")
    if flags:
        failed_high.append(f"flags present: {', '.join(flags)}")

    if failed_high:
        return Confidence.MEDIUM, failed_high

    reasons: list[str] = [
        "all evidence matched exactly and unambiguously",
        "at least one MEAT element",
        f"code in the top {config.high_confidence_max_rank} search results",
        "model certainty was high",
        "no flags",
    ]
    return Confidence.HIGH, reasons


def finalize(
    conditions: list[VerifiedCondition],
    selections: dict[int, ConditionSelection],
    candidates: list[list[Candidate]],
    config: PipelineConfig,
) -> tuple[list[Suggestion], list[DroppedItem]]:
    drafts, dropped = _build_drafts(conditions, selections, candidates)

    suggestions: list[Suggestion] = []
    for display_code, draft in drafts.items():
        flags = _reconcile_flags(draft, drafts)

        if "unspecified" in draft.candidate.description.lower():
            details = [
                detail
                for condition in conditions
                if condition.label in draft.condition_labels
                for detail in condition.specificity_details
            ]
            if details:
                flags.append(FLAG_UNDERSPECIFIED)

        meat = sorted({m for quote in draft.evidence for m in quote.meat}, key=lambda m: m.value)
        if not meat:
            flags.append(FLAG_NO_MEAT)
        # Model-reported specificity flags count as flags too: High means none.
        flags = flags + draft.specificity_flags

        confidence, reasons = _confidence(draft, flags, config)
        suggestions.append(
            Suggestion(
                code=display_code,
                description=draft.candidate.description,
                hcc_number=draft.candidate.hcc_number,
                hcc_label=draft.candidate.hcc_label,
                condition_label=" + ".join(draft.condition_labels),
                evidence=draft.evidence,
                meat=meat,
                confidence=confidence,
                confidence_reasons=reasons,
                candidate_rank=draft.candidate_rank,
                rationale=" ".join(draft.rationales),
                flags=flags,
            )
        )

    suggestions.sort(key=lambda s: s.code)
    return suggestions, dropped
