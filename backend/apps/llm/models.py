from django.db import models


class LlmCall(models.Model):
    """One AI call's metadata. Never stores note text, prompts, or responses.

    `run_id` is a plain UUID rather than a foreign key so this app has no
    dependency on the runs app (which arrives in Phase 3); the dashboard
    joins on it when needed.
    """

    class Step(models.TextChoices):
        EXTRACT = "extract"
        SELECT = "select"

    class Status(models.TextChoices):
        OK = "ok"
        ERROR = "error"

    run_id = models.UUIDField(null=True, blank=True, db_index=True)
    step = models.CharField(max_length=10, choices=Step.choices)
    model_name = models.CharField(max_length=100)
    prompt_version = models.CharField(max_length=10)
    request_hash = models.CharField(max_length=64)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    latency_ms = models.PositiveIntegerField(default=0)
    cache_hit = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=Status.choices)
    error_type = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.step} {self.status} ({self.created_at:%Y-%m-%d %H:%M})"


class LlmCache(models.Model):
    """Cached structured responses keyed by request hash.

    Hits cost nothing and make evaluation reruns free. The cached JSON is the
    model's structured output (not the note), kept so reruns can skip the API.
    """

    request_hash = models.CharField(max_length=64, unique=True)
    response_json = models.JSONField()
    model_name = models.CharField(max_length=100)
    prompt_version = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "LLM cache entries"

    def __str__(self) -> str:
        return f"{self.model_name} {self.request_hash[:12]}…"
