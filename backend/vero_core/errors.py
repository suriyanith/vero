"""Pipeline errors carry stable codes; raw exception text never reaches users."""

LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
LLM_RATE_LIMITED = "LLM_RATE_LIMITED"
LLM_BAD_OUTPUT = "LLM_BAD_OUTPUT"
INPUT_TOO_LARGE = "INPUT_TOO_LARGE"
PHI_DETECTED = "PHI_DETECTED"
WORKER_TIMEOUT = "WORKER_TIMEOUT"


class PipelineError(Exception):
    """An error with a stable, user-safe code."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class LLMError(PipelineError):
    """Raised by LLM clients after retries are exhausted or output is unusable."""
