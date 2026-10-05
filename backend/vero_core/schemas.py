"""Pydantic models for the pipeline.

Models sent to Gemini as response schemas (marked "AI output") use only plain
objects, lists, strings, integers, booleans, and enums, because the
structured-output schema subset is limited (no dict-typed fields).
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AIOutput(BaseModel):
    """Base for models sent to Gemini as response schemas.

    The structured-output API rejects schemas containing
    ``additionalProperties`` (which ``extra="forbid"`` emits), so AI-output
    models ignore unexpected fields instead of forbidding them. Everything
    the pipeline stores still goes through the Strict internal models.
    """

    model_config = ConfigDict(extra="ignore")


class ConditionStatus(StrEnum):
    ACTIVE = "active"
    HISTORICAL = "historical"
    RESOLVED = "resolved"
    UNCERTAIN = "uncertain"
    NEGATED = "negated"
    FAMILY_HISTORY = "family_history"


class Meat(StrEnum):
    MONITOR = "monitor"
    EVALUATE = "evaluate"
    ASSESS = "assess"
    TREAT = "treat"


class Certainty(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ---------- AI output: Step 1 (extract) ----------
class ExtractedQuote(AIOutput):
    text: str
    meat: list[Meat]


class ExtractedCondition(AIOutput):
    label: str
    status: ConditionStatus
    quotes: list[ExtractedQuote]
    specificity_details: list[str]


class ExtractionResult(AIOutput):
    conditions: list[ExtractedCondition]


# ---------- AI output: Step 4 (select, batched) ----------
class CodeChoice(AIOutput):
    code: str  # dotted code; must be in this condition's candidate list
    rationale: str


class ConditionSelection(AIOutput):
    condition_index: int  # matches the numbering in the prompt (1-based)
    codes: list[CodeChoice]
    no_fit: bool
    specificity_flags: list[str]
    certainty: Certainty


class SelectionResult(AIOutput):
    selections: list[ConditionSelection]


# ---------- Internal results (never sent to the AI) ----------
class VerifiedQuote(Strict):
    text: str  # exact substring of the original note
    start: int
    end: int
    meat: list[Meat]
    match_type: str  # "exact" or "case_insensitive"
    ambiguous: bool


class VerifiedCondition(Strict):
    label: str
    status: ConditionStatus
    quotes: list[VerifiedQuote]
    specificity_details: list[str]


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Candidate(Strict):
    """A real, retrieved code offered to the selection step."""

    code: str  # dotless, e.g. "E1122"
    display_code: str  # dotted, e.g. "E11.22"
    description: str
    is_billable: bool
    rank: int  # 1-based search rank; an expanded code inherits its source's rank
    category: str
    notes: dict[str, list[str]] = {}
    hcc_number: int | None = None
    hcc_label: str | None = None


class Suggestion(Strict):
    code: str  # dotted display code
    description: str
    hcc_number: int | None
    hcc_label: str | None
    condition_label: str
    evidence: list[VerifiedQuote]
    meat: list[Meat]
    confidence: Confidence
    confidence_reasons: list[str]
    candidate_rank: int
    rationale: str
    flags: list[str]


class DroppedItem(Strict):
    label: str
    reason: str  # "unverifiable_evidence", "out_of_candidates", "invalid_code", "no_selection"


class Usage(Strict):
    input_tokens: int
    output_tokens: int
    duration_ms: int
    dropped_quotes: int


class CodingResult(Strict):
    conditions: list[VerifiedCondition]
    suggestions: list[Suggestion]
    not_coded: list[VerifiedCondition]
    dropped: list[DroppedItem]
    usage: Usage


class AuditVerdict(StrEnum):
    SUPPORTED = "SUPPORTED"
    WEAK_SUPPORT = "WEAK_SUPPORT"
    SPECIFICITY_MISMATCH = "SPECIFICITY_MISMATCH"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    INVALID_CODE = "INVALID_CODE"
    MISSED_HCC = "MISSED_HCC"


class AuditFinding(Strict):
    submitted_code: str | None  # None for MISSED_HCC
    verdict: AuditVerdict
    reason_code: str  # e.g. "NOT_DOCUMENTED", "HISTORICAL", "UNCERTAIN"
    reason: str
    evidence: list[VerifiedQuote]
    suggested_code: str | None


class AuditResult(Strict):
    coding: CodingResult
    findings: list[AuditFinding]
