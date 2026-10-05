"""GeminiClient behavior with a stubbed SDK — never the real API."""

from dataclasses import dataclass, field
from typing import Any

import pytest
from google.genai import errors as genai_errors
from pydantic import BaseModel

from apps.llm.gemini import GeminiClient
from apps.llm.models import LlmCache, LlmCall
from vero_core.errors import LLM_BAD_OUTPUT, LLM_RATE_LIMITED, LLMError
from vero_core.schemas import ExtractionResult


class _Usage:
    prompt_token_count = 100
    candidates_token_count = 50


@dataclass
class _Response:
    parsed: BaseModel | None
    usage_metadata: Any = field(default_factory=_Usage)


class StubModels:
    """Stands in for google.genai Client.models."""

    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = outcomes
        self.calls: list[dict[str, Any]] = []

    def generate_content(self, **kwargs: Any) -> _Response:
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        assert isinstance(outcome, _Response)
        return outcome


@dataclass
class StubClient:
    models: StubModels


def make_client(outcomes: list[Any], max_rpm: int = 1000) -> tuple[GeminiClient, StubModels]:
    sleeps: list[float] = []
    client = GeminiClient(
        api_key="test-key",
        model_name="gemini-test",
        max_rpm=max_rpm,
        timeout_seconds=5,
        max_output_tokens=1024,
        sleep=sleeps.append,
    )
    stub = StubModels(outcomes)
    client._client = StubClient(models=stub)  # type: ignore[assignment]
    client._sleeps = sleeps  # type: ignore[attr-defined]
    return client, stub


def generate(client: GeminiClient) -> Any:
    return client.generate(
        step="extract",
        prompt_id="extract",
        prompt_version="v1",
        variables={"note_text": "CKD stage 3a stable."},
        output_model=ExtractionResult,
    )


GOOD = ExtractionResult(conditions=[])


@pytest.mark.django_db
class TestGenerateAndCache:
    def test_success_logs_call_and_caches(self) -> None:
        client, stub = make_client([_Response(parsed=GOOD)])
        result = generate(client)
        assert isinstance(result.parsed, ExtractionResult)
        assert result.input_tokens == 100 and result.output_tokens == 50
        assert not result.cache_hit

        call = LlmCall.objects.get()
        assert call.status == "ok" and not call.cache_hit
        assert call.input_tokens == 100
        assert LlmCache.objects.count() == 1

    def test_identical_request_hits_cache_without_api_call(self) -> None:
        client, stub = make_client([_Response(parsed=GOOD)])
        generate(client)
        result = generate(client)  # same inputs -> same request hash
        assert result.cache_hit
        assert len(stub.calls) == 1  # no second API call
        assert LlmCall.objects.filter(cache_hit=True).count() == 1

    def test_different_note_misses_cache(self) -> None:
        client, stub = make_client([_Response(parsed=GOOD), _Response(parsed=GOOD)])
        generate(client)
        client.generate(
            step="extract",
            prompt_id="extract",
            prompt_version="v1",
            variables={"note_text": "a different note"},
            output_model=ExtractionResult,
        )
        assert len(stub.calls) == 2

    def test_system_and_user_content_sent_structured(self) -> None:
        client, stub = make_client([_Response(parsed=GOOD)])
        generate(client)
        [call] = stub.calls
        config = call["config"]
        assert "certified medical coder" in config.system_instruction
        assert "<note>" in call["contents"]
        assert config.response_mime_type == "application/json"
        assert config.response_schema is ExtractionResult


@pytest.mark.django_db
class TestRetries:
    def test_rate_limit_retries_then_fails_with_stable_code(self) -> None:
        error = genai_errors.ClientError(429, {"error": {"message": "quota"}})
        client, stub = make_client([error] * 5)
        with pytest.raises(LLMError) as excinfo:
            generate(client)
        assert excinfo.value.code == LLM_RATE_LIMITED
        assert len(stub.calls) == 5  # MAX_ATTEMPTS
        # 429 waits out the minute window instead of hammering it
        assert any(wait >= 60 for wait in client._sleeps)  # type: ignore[attr-defined]
        assert LlmCall.objects.get().status == "error"

    def test_server_error_then_success(self) -> None:
        error = genai_errors.ServerError(500, {"error": {"message": "boom"}})
        client, stub = make_client([error, _Response(parsed=GOOD)])
        result = generate(client)
        assert isinstance(result.parsed, ExtractionResult)
        assert len(stub.calls) == 2

    def test_non_retryable_client_error_fails_immediately(self) -> None:
        error = genai_errors.ClientError(400, {"error": {"message": "bad request"}})
        client, stub = make_client([error])
        with pytest.raises(LLMError):
            generate(client)
        assert len(stub.calls) == 1

    def test_unparseable_output_retries_once_then_bad_output(self) -> None:
        client, stub = make_client([_Response(parsed=None), _Response(parsed=None)])
        with pytest.raises(LLMError) as excinfo:
            generate(client)
        assert excinfo.value.code == LLM_BAD_OUTPUT
        assert len(stub.calls) == 2


@pytest.mark.django_db
class TestRateLimiter:
    def test_spaces_calls_beyond_the_rpm_budget(self) -> None:
        responses = [_Response(parsed=GOOD), _Response(parsed=GOOD)]
        client, stub = make_client(responses, max_rpm=1)
        generate(client)
        LlmCache.objects.all().delete()  # force the second call through
        generate(client)
        sleeps: list[float] = client._sleeps  # type: ignore[attr-defined]
        assert any(wait > 50 for wait in sleeps)  # waited most of the minute
