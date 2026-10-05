"""Test double for the LLM: canned responses, zero network, zero cost.

Used by all automated tests and CI (`VERO_LLM_MODE=fake`), and by the CLI's
fake mode. Responses are supplied per step, either as parsed objects or as
functions of the rendered variables (for tests that need to react to input).
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from vero_core.errors import LLM_BAD_OUTPUT, LLMError
from vero_core.interfaces import LLMResult

Responder = BaseModel | Callable[[dict[str, Any]], BaseModel]


@dataclass
class RecordedCall:
    step: str
    prompt_id: str
    prompt_version: str
    variables: dict[str, Any]
    output_model: type[BaseModel]


@dataclass
class FakeLLMClient:
    responses: dict[str, Responder]
    calls: list[RecordedCall] = field(default_factory=list)

    def generate(
        self,
        *,
        step: str,
        prompt_id: str,
        prompt_version: str,
        variables: dict[str, Any],
        output_model: type[BaseModel],
    ) -> LLMResult:
        self.calls.append(
            RecordedCall(
                step=step,
                prompt_id=prompt_id,
                prompt_version=prompt_version,
                variables=variables,
                output_model=output_model,
            )
        )
        responder = self.responses.get(step)
        if responder is None:
            raise LLMError(LLM_BAD_OUTPUT, f"FakeLLMClient has no response for step {step!r}")
        parsed = responder(variables) if callable(responder) else responder
        if not isinstance(parsed, output_model):
            raise LLMError(
                LLM_BAD_OUTPUT,
                f"Fake response for {step!r} is {type(parsed).__name__}, "
                f"expected {output_model.__name__}",
            )
        return LLMResult(
            parsed=parsed, input_tokens=0, output_tokens=0, latency_ms=0, cache_hit=False
        )
