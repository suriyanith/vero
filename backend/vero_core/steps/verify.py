"""Step 2 — Verify quotes (Python).

This step is what makes "Vero never invents evidence" a guarantee rather
than a hope: every quote must be found in the note, or it is dropped; a
condition with no surviving quote is dropped entirely.
"""

from dataclasses import dataclass

from vero_core.schemas import DroppedItem, ExtractionResult, VerifiedCondition, VerifiedQuote
from vero_core.text import find_quote, normalize


@dataclass(frozen=True)
class VerifyOutcome:
    conditions: list[VerifiedCondition]
    dropped: list[DroppedItem]
    dropped_quotes: int


def verify_conditions(note_text: str, extraction: ExtractionResult) -> VerifyOutcome:
    normalized_note = normalize(note_text)
    conditions: list[VerifiedCondition] = []
    dropped: list[DroppedItem] = []
    dropped_quotes = 0

    for condition in extraction.conditions:
        verified_quotes: list[VerifiedQuote] = []
        for quote in condition.quotes:
            match = find_quote(note_text, normalized_note, quote.text)
            if match is None:
                dropped_quotes += 1
                continue
            verified_quotes.append(
                VerifiedQuote(
                    text=match.text,
                    start=match.start,
                    end=match.end,
                    meat=quote.meat,
                    match_type=match.match_type,
                    ambiguous=match.ambiguous,
                )
            )
        if verified_quotes:
            conditions.append(
                VerifiedCondition(
                    label=condition.label,
                    status=condition.status,
                    quotes=verified_quotes,
                    specificity_details=condition.specificity_details,
                )
            )
        else:
            dropped.append(DroppedItem(label=condition.label, reason="unverifiable_evidence"))

    return VerifyOutcome(conditions=conditions, dropped=dropped, dropped_quotes=dropped_quotes)
