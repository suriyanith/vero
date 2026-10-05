"""The two seams between the pipeline and the outside world.

Django code implements these; `vero_core` only ever sees the protocols, which
is what keeps the pipeline framework-free and unit-testable.
"""

from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel

from vero_core.schemas import Candidate


@dataclass(frozen=True)
class LLMResult:
    parsed: BaseModel
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cache_hit: bool


class LLMClient(Protocol):
    def generate(
        self,
        *,
        step: str,  # "extract" or "select"
        prompt_id: str,
        prompt_version: str,
        variables: dict[str, Any],  # rendered into the prompt template
        output_model: type[BaseModel],
    ) -> LLMResult: ...


class CodeRepository(Protocol):
    def search(self, query: str, limit: int = 10, billable_only: bool = True) -> list[Candidate]:
        """Ranked candidates; an implementation's rank starts at 1."""
        ...

    def get(self, display_code: str) -> Candidate | None: ...

    def billable_in_category(self, category: str) -> list[Candidate]: ...


@dataclass(frozen=True)
class PipelineDeps:
    llm: LLMClient
    codes: CodeRepository


class PipelineConfig(BaseModel):
    """Everything tunable about a run. Values come from settings, not literals."""

    model_name: str = "fake"
    extract_prompt_version: str = "v1"
    select_prompt_version: str = "v1"
    retrieval_top_k: int = 10
    category_expansion_top: int = 3  # expand categories of this many top results
    max_candidates_per_condition: int = 25
    high_confidence_max_rank: int = 3  # High requires the code within this rank
    low_confidence_min_rank: int = 11  # at or beyond this rank, confidence is Low

    @property
    def prompt_versions(self) -> dict[str, str]:
        return {"extract": self.extract_prompt_version, "select": self.select_prompt_version}
