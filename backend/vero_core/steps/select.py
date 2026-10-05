"""Step 4 — Select codes (AI call 2, one batched call for all conditions)."""

from dataclasses import dataclass

from vero_core.interfaces import LLMResult, PipelineConfig, PipelineDeps
from vero_core.schemas import (
    Candidate,
    CodeChoice,
    ConditionSelection,
    SelectionResult,
    VerifiedCondition,
)

# Candidate note types shown to the selector, in display order.
_NOTE_LABELS = (
    ("excludes1", "Excludes1"),
    ("code_first", "Code first"),
    ("use_additional", "Use additional code"),
)
_MAX_NOTE_LINES_PER_TYPE = 4


def _candidate_lines(candidates: list[Candidate]) -> list[str]:
    lines = []
    for number, candidate in enumerate(candidates, start=1):
        lines.append(f"{number}. {candidate.display_code} — {candidate.description}")
        for key, label in _NOTE_LABELS:
            for note in candidate.notes.get(key, [])[:_MAX_NOTE_LINES_PER_TYPE]:
                lines.append(f"   {label}: {note}")
    return lines


def build_conditions_block(
    conditions: list[VerifiedCondition], candidates: list[list[Candidate]]
) -> str:
    blocks = []
    for index, (condition, condition_candidates) in enumerate(
        zip(conditions, candidates, strict=True), start=1
    ):
        lines = [f"Condition {index}: {condition.label}"]
        details = ", ".join(condition.specificity_details) or "none stated"
        lines.append(f"Specificity details: {details}")
        lines.append("Evidence:")
        for quote in condition.quotes:
            meat = ", ".join(m.value for m in quote.meat) or "none"
            lines.append(f'- "{quote.text}" (MEAT: {meat})')
        lines.append("Candidates:")
        lines.extend(_candidate_lines(condition_candidates))
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


@dataclass(frozen=True)
class SelectOutcome:
    # condition index (1-based, matching the prompt) -> validated selection
    selections: dict[int, ConditionSelection]
    # (condition index, code) choices discarded because they were not candidates
    out_of_candidates: list[tuple[int, str]]
    llm_result: LLMResult


def select_codes(
    conditions: list[VerifiedCondition],
    candidates: list[list[Candidate]],
    deps: PipelineDeps,
    config: PipelineConfig,
) -> SelectOutcome:
    result = deps.llm.generate(
        step="select",
        prompt_id="select",
        prompt_version=config.select_prompt_version,
        variables={"conditions_block": build_conditions_block(conditions, candidates)},
        output_model=SelectionResult,
    )
    assert isinstance(result.parsed, SelectionResult)

    selections: dict[int, ConditionSelection] = {}
    out_of_candidates: list[tuple[int, str]] = []
    for selection in result.parsed.selections:
        index = selection.condition_index
        if not 1 <= index <= len(conditions) or index in selections:
            continue  # hallucinated or duplicate index: ignore the entry
        allowed = {c.display_code for c in candidates[index - 1]}
        kept: list[CodeChoice] = []
        for choice in selection.codes:
            if choice.code in allowed:
                kept.append(choice)
            else:
                out_of_candidates.append((index, choice.code))
        selections[index] = selection.model_copy(update={"codes": kept})

    return SelectOutcome(
        selections=selections, out_of_candidates=out_of_candidates, llm_result=result
    )
