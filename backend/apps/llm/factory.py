"""Choose the LLM client implementation from settings.

`fake` mode exists so the whole stack runs without a key or network: it
returns empty results (tests inject their own canned responses instead).
"""

import uuid

from django.conf import settings

from apps.llm.gemini import GeminiClient
from vero_core.fake_llm import FakeLLMClient
from vero_core.interfaces import LLMClient
from vero_core.schemas import ExtractionResult, SelectionResult


def build_llm_client(run_id: uuid.UUID | None = None) -> LLMClient:
    if settings.VERO_LLM_MODE == "live":
        return GeminiClient.from_settings(run_id=run_id)
    return FakeLLMClient(
        responses={
            "extract": ExtractionResult(conditions=[]),
            "select": SelectionResult(selections=[]),
        }
    )
