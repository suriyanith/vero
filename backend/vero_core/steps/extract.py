"""Step 1 — Extract conditions (AI call 1)."""

from vero_core.interfaces import LLMResult, PipelineConfig, PipelineDeps
from vero_core.schemas import ExtractionResult


def extract_conditions(
    note_text: str, deps: PipelineDeps, config: PipelineConfig
) -> tuple[ExtractionResult, LLMResult]:
    result = deps.llm.generate(
        step="extract",
        prompt_id="extract",
        prompt_version=config.extract_prompt_version,
        variables={"note_text": note_text},
        output_model=ExtractionResult,
    )
    assert isinstance(result.parsed, ExtractionResult)
    return result.parsed, result
