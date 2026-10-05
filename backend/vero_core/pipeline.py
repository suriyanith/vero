"""Pipeline entry points.

Exactly two AI calls per note (extract and select); everything else is
deterministic Python. `audit_note` arrives in Phase 5.
"""

import time

from vero_core.interfaces import PipelineConfig, PipelineDeps
from vero_core.schemas import (
    Candidate,
    CodingResult,
    ConditionStatus,
    DroppedItem,
    Suggestion,
    Usage,
    VerifiedCondition,
)
from vero_core.steps.extract import extract_conditions
from vero_core.steps.finalize import finalize
from vero_core.steps.retrieve import retrieve_candidates
from vero_core.steps.select import select_codes
from vero_core.steps.verify import verify_conditions


def code_note(note_text: str, deps: PipelineDeps, config: PipelineConfig) -> CodingResult:
    started = time.monotonic()
    input_tokens = output_tokens = 0

    # Step 1 — extract (AI call 1). A failure here fails the whole run.
    extraction, extract_llm = extract_conditions(note_text, deps, config)
    input_tokens += extract_llm.input_tokens
    output_tokens += extract_llm.output_tokens

    # Step 2 — verify quotes against the note.
    verified = verify_conditions(note_text, extraction)
    dropped = list(verified.dropped)

    active: list[VerifiedCondition] = []
    not_coded: list[VerifiedCondition] = []
    for condition in verified.conditions:
        (active if condition.status == ConditionStatus.ACTIVE else not_coded).append(condition)

    suggestions: list[Suggestion] = []
    if active:
        # Step 3 — retrieve candidates for each active condition.
        candidates: list[list[Candidate]] = [
            retrieve_candidates(condition, deps.codes, config) for condition in active
        ]

        # Step 4 — select (AI call 2, batched over all active conditions).
        selection = select_codes(active, candidates, deps, config)
        input_tokens += selection.llm_result.input_tokens
        output_tokens += selection.llm_result.output_tokens
        for index, code in selection.out_of_candidates:
            dropped.append(
                DroppedItem(label=f"{active[index - 1].label}: {code}", reason="out_of_candidates")
            )

        # Step 5 — finalize.
        suggestions, finalize_dropped = finalize(active, selection.selections, candidates, config)
        dropped.extend(finalize_dropped)

    duration_ms = int((time.monotonic() - started) * 1000)
    return CodingResult(
        conditions=verified.conditions,
        suggestions=suggestions,
        not_coded=not_coded,
        dropped=dropped,
        usage=Usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration_ms=duration_ms,
            dropped_quotes=verified.dropped_quotes,
        ),
    )
