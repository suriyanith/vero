"""Small builders so tests state only what they care about."""

from vero_core.schemas import (
    Candidate,
    Certainty,
    CodeChoice,
    ConditionSelection,
    ConditionStatus,
    Meat,
    VerifiedCondition,
    VerifiedQuote,
)


def quote(
    text: str = "some evidence",
    start: int = 0,
    end: int = 13,
    meat: list[Meat] | None = None,
    match_type: str = "exact",
    ambiguous: bool = False,
) -> VerifiedQuote:
    return VerifiedQuote(
        text=text,
        start=start,
        end=end,
        meat=meat if meat is not None else [Meat.ASSESS],
        match_type=match_type,
        ambiguous=ambiguous,
    )


def condition(
    label: str = "type 2 diabetes",
    status: ConditionStatus = ConditionStatus.ACTIVE,
    quotes: list[VerifiedQuote] | None = None,
    specificity_details: list[str] | None = None,
) -> VerifiedCondition:
    return VerifiedCondition(
        label=label,
        status=status,
        quotes=quotes if quotes is not None else [quote()],
        specificity_details=specificity_details or [],
    )


def candidate(
    display_code: str = "E11.9",
    description: str = "Type 2 diabetes mellitus without complications",
    rank: int = 1,
    is_billable: bool = True,
    notes: dict[str, list[str]] | None = None,
    hcc_number: int | None = None,
    hcc_label: str | None = None,
) -> Candidate:
    dotless = display_code.replace(".", "")
    return Candidate(
        code=dotless,
        display_code=display_code,
        description=description,
        is_billable=is_billable,
        rank=rank,
        category=dotless[:3],
        notes=notes or {},
        hcc_number=hcc_number,
        hcc_label=hcc_label,
    )


def selection(
    index: int = 1,
    codes: list[tuple[str, str]] | None = None,
    no_fit: bool = False,
    specificity_flags: list[str] | None = None,
    certainty: Certainty = Certainty.HIGH,
) -> ConditionSelection:
    chosen = codes if codes is not None else [("E11.9", "matches the documentation")]
    return ConditionSelection(
        condition_index=index,
        codes=[CodeChoice(code=code, rationale=rationale) for code, rationale in chosen],
        no_fit=no_fit,
        specificity_flags=specificity_flags or [],
        certainty=certainty,
    )
