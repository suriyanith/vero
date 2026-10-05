from vero_core.schemas import (
    ConditionStatus,
    ExtractedCondition,
    ExtractedQuote,
    ExtractionResult,
    Meat,
)
from vero_core.steps.verify import verify_conditions

NOTE = (
    "HPI: 72-year-old with type 2 diabetes and CKD stage 3a.\n"
    "Denies chest pain. Trace bilateral ankle edema.\n"
    "1. Type 2 diabetes with CKD stage 3a - A1c 7.4%, continue metformin.\n"
)


def extraction(*conditions: ExtractedCondition) -> ExtractionResult:
    return ExtractionResult(conditions=list(conditions))


def extracted(
    label: str,
    *quotes: str,
    status: ConditionStatus = ConditionStatus.ACTIVE,
    meat: list[Meat] | None = None,
) -> ExtractedCondition:
    return ExtractedCondition(
        label=label,
        status=status,
        quotes=[ExtractedQuote(text=q, meat=meat or []) for q in quotes],
        specificity_details=[],
    )


class TestVerifyConditions:
    def test_verified_quote_has_original_offsets(self) -> None:
        outcome = verify_conditions(
            NOTE, extraction(extracted("diabetes", "type 2 diabetes and CKD stage 3a"))
        )
        [condition] = outcome.conditions
        [quote] = condition.quotes
        assert NOTE[quote.start : quote.end] == quote.text
        assert quote.match_type == "exact"
        assert outcome.dropped_quotes == 0

    def test_invented_quote_is_dropped_and_counted(self) -> None:
        outcome = verify_conditions(
            NOTE,
            extraction(
                extracted("diabetes", "type 2 diabetes and CKD stage 3a", "A1c improved to 6.8%")
            ),
        )
        [condition] = outcome.conditions
        assert len(condition.quotes) == 1
        assert outcome.dropped_quotes == 1

    def test_condition_with_no_surviving_quote_is_dropped(self) -> None:
        outcome = verify_conditions(
            NOTE, extraction(extracted("hypertension", "BP is elevated today"))
        )
        assert outcome.conditions == []
        [dropped] = outcome.dropped
        assert dropped.label == "hypertension"
        assert dropped.reason == "unverifiable_evidence"
        assert outcome.dropped_quotes == 1

    def test_meat_tags_survive_verification(self) -> None:
        outcome = verify_conditions(
            NOTE,
            extraction(extracted("diabetes", "continue metformin", meat=[Meat.TREAT])),
        )
        assert outcome.conditions[0].quotes[0].meat == [Meat.TREAT]

    def test_status_passes_through(self) -> None:
        outcome = verify_conditions(
            NOTE,
            extraction(
                extracted("chest pain", "Denies chest pain", status=ConditionStatus.NEGATED)
            ),
        )
        assert outcome.conditions[0].status == ConditionStatus.NEGATED
