"""Audit mode: classify already-submitted codes against the coding result.

Pure Python — reuses the coding pipeline's output and the code repository;
no extra AI calls. The checks run in a strict order (first match wins), then
a two-way pass reports documented HCC conditions that were never submitted.
"""

from vero_core.interfaces import CodeRepository, PipelineConfig
from vero_core.schemas import (
    AuditFinding,
    AuditVerdict,
    CodingResult,
    Suggestion,
    VerifiedCondition,
)

NOT_DOCUMENTED = "NOT_DOCUMENTED"
NOT_SUBMITTED = "NOT_SUBMITTED"

# How many search results to scan when linking a submitted code to a
# documented-but-not-codeable condition (check 5).
NON_CODED_SEARCH_LIMIT = 10


def _dotless(code: str) -> str:
    return code.replace(".", "").upper()


def _category(code: str) -> str:
    return _dotless(code)[:3]


def _match_suggestion(code: str, suggestions: list[Suggestion]) -> Suggestion | None:
    return next((s for s in suggestions if _dotless(s.code) == _dotless(code)), None)


def _related_suggestion(
    code: str, hcc_number: int | None, suggestions: list[Suggestion]
) -> Suggestion | None:
    """A suggestion in the same 3-char category or the same HCC, but different."""
    for suggestion in suggestions:
        if _dotless(suggestion.code) == _dotless(code):
            continue
        same_category = _category(suggestion.code) == _category(code)
        same_hcc = hcc_number is not None and suggestion.hcc_number == hcc_number
        if same_category or same_hcc:
            return suggestion
    return None


def _matching_non_coded(
    code: str, conditions: list[VerifiedCondition], repo: CodeRepository
) -> VerifiedCondition | None:
    """Does this code plausibly encode a condition Vero refused to code?

    Search the code set with the condition's label; the submitted code (or
    its category) appearing in the top results links them.
    """
    for condition in conditions:
        hits = repo.search(condition.label, limit=NON_CODED_SEARCH_LIMIT)
        for hit in hits:
            if hit.code == _dotless(code) or hit.category == _category(code):
                return condition
    return None


def classify_submitted_code(code: str, coding: CodingResult, repo: CodeRepository) -> AuditFinding:
    candidate = repo.get(code)

    # 1. Not a real, billable code.
    if candidate is None or not candidate.is_billable:
        return AuditFinding(
            submitted_code=code.upper(),
            verdict=AuditVerdict.INVALID_CODE,
            reason_code="INVALID_CODE",
            reason=f"{code.upper()} is not a billable code in the active ICD-10-CM code set.",
            evidence=[],
            suggested_code=None,
        )

    display = candidate.display_code

    # 2 & 3. Exact match against a suggestion.
    suggestion = _match_suggestion(display, coding.suggestions)
    if suggestion is not None:
        if suggestion.meat:
            return AuditFinding(
                submitted_code=display,
                verdict=AuditVerdict.SUPPORTED,
                reason_code="SUPPORTED",
                reason="The note supports this code with MEAT evidence.",
                evidence=suggestion.evidence,
                suggested_code=None,
            )
        return AuditFinding(
            submitted_code=display,
            verdict=AuditVerdict.WEAK_SUPPORT,
            reason_code="NO_MEAT",
            reason="Documented, but not monitored, evaluated, assessed, or treated at this visit.",
            evidence=suggestion.evidence,
            suggested_code=None,
        )

    # 4. Same family or HCC as a suggestion, but a different code.
    related = _related_suggestion(display, candidate.hcc_number, coding.suggestions)
    if related is not None:
        return AuditFinding(
            submitted_code=display,
            verdict=AuditVerdict.SPECIFICITY_MISMATCH,
            reason_code="SPECIFICITY_MISMATCH",
            reason=f"The note supports {related.code} ({related.description}) instead.",
            evidence=related.evidence,
            suggested_code=related.code,
        )

    # 5. Encodes a condition Vero deliberately left uncoded.
    non_coded = _matching_non_coded(display, coding.not_coded, repo)
    if non_coded is not None:
        status = non_coded.status.value.upper()
        return AuditFinding(
            submitted_code=display,
            verdict=AuditVerdict.NOT_SUPPORTED,
            reason_code=status,
            reason=(
                f"{non_coded.label} is documented as {non_coded.status.value.replace('_', ' ')},"
                " which is not codeable for this visit."
            ),
            evidence=non_coded.quotes[:1],
            suggested_code=None,
        )

    # 6. Nothing in the note backs it.
    return AuditFinding(
        submitted_code=display,
        verdict=AuditVerdict.NOT_SUPPORTED,
        reason_code=NOT_DOCUMENTED,
        reason="Nothing in the note documents this condition.",
        evidence=[],
        suggested_code=None,
    )


def missed_hcc_findings(
    submitted_codes: list[str], coding: CodingResult, existing: list[AuditFinding]
) -> list[AuditFinding]:
    """Two-way review: HCC-mapped suggestions neither submitted nor already offered."""
    submitted = {_dotless(code) for code in submitted_codes}
    offered = {_dotless(f.suggested_code) for f in existing if f.suggested_code}
    findings = []
    for suggestion in coding.suggestions:
        if suggestion.hcc_number is None:
            continue
        if _dotless(suggestion.code) in submitted or _dotless(suggestion.code) in offered:
            continue
        findings.append(
            AuditFinding(
                submitted_code=None,
                verdict=AuditVerdict.MISSED_HCC,
                reason_code=NOT_SUBMITTED,
                reason=(
                    f"{suggestion.code} ({suggestion.description}) maps to HCC "
                    f"{suggestion.hcc_number} and is documented but was not submitted."
                ),
                evidence=suggestion.evidence,
                suggested_code=suggestion.code,
            )
        )
    return findings


def audit_findings(
    submitted_codes: list[str],
    coding: CodingResult,
    repo: CodeRepository,
    config: PipelineConfig,
) -> list[AuditFinding]:
    # Dedupe on the dotless form but keep the first original spelling so an
    # invalid code is echoed back the way the user wrote it.
    deduped: dict[str, str] = {}
    for code in submitted_codes:
        deduped.setdefault(_dotless(code), code)
    findings = [classify_submitted_code(code, coding, repo) for code in deduped.values()]
    findings.extend(missed_hcc_findings(submitted_codes, coding, findings))
    return findings
