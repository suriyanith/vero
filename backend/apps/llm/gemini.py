"""GeminiClient: the live implementation of vero_core's LLMClient protocol.

Adds what the pipeline must not know about: prompt rendering into API calls,
structured output, retries with backoff, a client-side rate limiter for the
free tier, response caching, and per-call usage logging.
"""

import hashlib
import json
import logging
import time
import uuid
from collections import deque
from collections.abc import Callable
from typing import Any

from django.conf import settings
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from pydantic import BaseModel, ValidationError

from apps.llm.models import LlmCache, LlmCall
from vero_core.errors import LLM_BAD_OUTPUT, LLM_RATE_LIMITED, LLM_UNAVAILABLE, LLMError
from vero_core.interfaces import LLMResult
from vero_core.prompt_loader import load_prompt, render

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5  # for rate-limit and server errors
BACKOFF_BASE_SECONDS = 3.0  # 3s, 6s, 12s, 24s — Gemini capacity spikes are bursty
RATE_LIMIT_BACKOFF_SECONDS = 62.0  # 429 quotas reset on minute windows


class GeminiClient:
    def __init__(
        self,
        *,
        api_key: str,
        model_name: str,
        max_rpm: int,
        timeout_seconds: int,
        max_output_tokens: int,
        run_id: uuid.UUID | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not api_key:
            raise LLMError(LLM_UNAVAILABLE, "GEMINI_API_KEY is not set.")
        if not model_name:
            raise LLMError(LLM_UNAVAILABLE, "GEMINI_MODEL is not set.")
        self.model_name = model_name
        self.max_rpm = max_rpm
        self.max_output_tokens = max_output_tokens
        self.run_id = run_id
        self._sleep = sleep
        self._recent_calls: deque[float] = deque()
        self._client = genai.Client(
            api_key=api_key,
            http_options=genai_types.HttpOptions(timeout=timeout_seconds * 1000),
        )

    @classmethod
    def from_settings(cls, run_id: uuid.UUID | None = None) -> "GeminiClient":
        return cls(
            api_key=settings.GEMINI_API_KEY,
            model_name=settings.GEMINI_MODEL,
            max_rpm=settings.VERO_LLM_MAX_RPM,
            timeout_seconds=settings.VERO_LLM_TIMEOUT_SECONDS,
            max_output_tokens=settings.VERO_LLM_MAX_OUTPUT_TOKENS,
            run_id=run_id,
        )

    # ---- LLMClient protocol ----

    def generate(
        self,
        *,
        step: str,
        prompt_id: str,
        prompt_version: str,
        variables: dict[str, Any],
        output_model: type[BaseModel],
    ) -> LLMResult:
        template = load_prompt(prompt_id, prompt_version)
        user_content = render(template.user, variables)
        request_hash = self._request_hash(
            prompt_id, prompt_version, template.system, user_content, output_model
        )

        cached = LlmCache.objects.filter(request_hash=request_hash).first()
        if cached is not None:
            parsed = output_model.model_validate(cached.response_json)
            self._log(step, prompt_version, request_hash, 0, 0, 0, cache_hit=True, status="ok")
            return LLMResult(
                parsed=parsed, input_tokens=0, output_tokens=0, latency_ms=0, cache_hit=True
            )

        started = time.monotonic()
        try:
            parsed, input_tokens, output_tokens = self._call_with_retries(
                template.system, user_content, output_model
            )
        except LLMError as exc:
            latency_ms = int((time.monotonic() - started) * 1000)
            self._log(
                step,
                prompt_version,
                request_hash,
                0,
                0,
                latency_ms,
                cache_hit=False,
                status="error",
                error_type=exc.code,
            )
            raise

        latency_ms = int((time.monotonic() - started) * 1000)
        LlmCache.objects.update_or_create(
            request_hash=request_hash,
            defaults={
                "response_json": parsed.model_dump(mode="json"),
                "model_name": self.model_name,
                "prompt_version": prompt_version,
            },
        )
        self._log(
            step,
            prompt_version,
            request_hash,
            input_tokens,
            output_tokens,
            latency_ms,
            cache_hit=False,
            status="ok",
        )
        return LLMResult(
            parsed=parsed,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cache_hit=False,
        )

    # ---- internals ----

    def _request_hash(
        self,
        prompt_id: str,
        prompt_version: str,
        system: str,
        user_content: str,
        output_model: type[BaseModel],
    ) -> str:
        schema_json = json.dumps(output_model.model_json_schema(), sort_keys=True)
        payload = "\x00".join(
            [self.model_name, prompt_id, prompt_version, system, user_content, schema_json]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _wait_for_rate_limit(self) -> None:
        now = time.monotonic()
        window_start = now - 60
        while self._recent_calls and self._recent_calls[0] < window_start:
            self._recent_calls.popleft()
        if len(self._recent_calls) >= self.max_rpm:
            wait = self._recent_calls[0] + 60 - now
            if wait > 0:
                logger.info("Rate limiter: waiting %.1fs", wait)
                self._sleep(wait)
        self._recent_calls.append(time.monotonic())

    def _call_once(
        self, system: str, user_content: str, output_model: type[BaseModel]
    ) -> tuple[BaseModel | None, int, int]:
        self._wait_for_rate_limit()
        response = self._client.models.generate_content(
            model=self.model_name,
            contents=user_content,
            config=genai_types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_schema=output_model,
                max_output_tokens=self.max_output_tokens,
            ),
        )
        usage = response.usage_metadata
        input_tokens = (usage.prompt_token_count or 0) if usage else 0
        output_tokens = (usage.candidates_token_count or 0) if usage else 0
        parsed = response.parsed
        if parsed is not None and not isinstance(parsed, output_model):
            try:
                parsed = output_model.model_validate(parsed)
            except ValidationError:
                parsed = None
        return parsed, input_tokens, output_tokens

    def _call_with_retries(
        self, system: str, user_content: str, output_model: type[BaseModel]
    ) -> tuple[BaseModel, int, int]:
        bad_output_retries = 1  # a malformed/truncated response gets one retry
        attempt = 0
        while True:
            attempt += 1
            try:
                parsed, input_tokens, output_tokens = self._call_once(
                    system, user_content, output_model
                )
            except genai_errors.APIError as exc:
                retryable = isinstance(exc, genai_errors.ServerError) or exc.code == 429
                if not retryable:
                    raise LLMError(LLM_UNAVAILABLE, f"Gemini request failed ({exc.code})") from exc
                if attempt >= MAX_ATTEMPTS:
                    code = LLM_RATE_LIMITED if exc.code == 429 else LLM_UNAVAILABLE
                    raise LLMError(code, "Gemini retries exhausted") from exc
                backoff = BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
                if exc.code == 429:
                    # Quota windows are per-minute; retrying sooner just burns
                    # attempts inside the same exhausted window.
                    backoff = max(backoff, RATE_LIMIT_BACKOFF_SECONDS)
                logger.warning("Gemini error %s; retrying in %.0fs", exc.code, backoff)
                self._sleep(backoff)
                continue

            if parsed is None:
                # None means malformed output or the output-token limit was hit.
                if bad_output_retries > 0:
                    bad_output_retries -= 1
                    logger.warning("Gemini returned unparseable output; retrying once")
                    continue
                raise LLMError(LLM_BAD_OUTPUT, "Gemini output did not match the schema")
            return parsed, input_tokens, output_tokens

    def _log(
        self,
        step: str,
        prompt_version: str,
        request_hash: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        *,
        cache_hit: bool,
        status: str,
        error_type: str = "",
    ) -> None:
        LlmCall.objects.create(
            run_id=self.run_id,
            step=step,
            model_name=self.model_name,
            prompt_version=prompt_version,
            request_hash=request_hash,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cache_hit=cache_hit,
            status=status,
            error_type=error_type,
        )
