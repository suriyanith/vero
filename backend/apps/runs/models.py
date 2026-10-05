import uuid

from django.conf import settings
from django.db import models

from apps.notes.models import Mode, Note
from apps.reference.models import CodeSetVersion, HccModel


class Run(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued"
        PROCESSING = "processing"
        READY_FOR_REVIEW = "ready_for_review"
        COMPLETED = "completed"
        FAILED = "failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="runs")
    mode = models.CharField(max_length=10, choices=Mode.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    submitted_codes = models.JSONField(default=list, blank=True)  # audit mode only
    retry_of = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="retries"
    )
    pipeline_version = models.CharField(max_length=20, default="1")
    prompt_versions = models.JSONField(default=dict, blank=True)
    model_name = models.CharField(max_length=100, blank=True)
    code_set = models.ForeignKey(CodeSetVersion, null=True, on_delete=models.PROTECT)
    hcc_model = models.ForeignKey(HccModel, null=True, on_delete=models.PROTECT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    dropped_quotes = models.PositiveIntegerField(default=0)
    error_code = models.CharField(max_length=30, blank=True)
    # Safe for users; never a stack trace or raw exception text.
    error_message = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self) -> str:
        return f"{self.mode} run {self.id} ({self.status})"


class Condition(models.Model):
    class ConditionStatus(models.TextChoices):
        ACTIVE = "active"
        HISTORICAL = "historical"
        RESOLVED = "resolved"
        UNCERTAIN = "uncertain"
        NEGATED = "negated"
        FAMILY_HISTORY = "family_history"

    run = models.ForeignKey(Run, on_delete=models.CASCADE, related_name="conditions")
    label = models.CharField(max_length=300)
    status = models.CharField(max_length=15, choices=ConditionStatus.choices)
    specificity_details = models.JSONField(default=list, blank=True)
    # [{text, start, end, meat, match_type, ambiguous}]
    quotes = models.JSONField(default=list, blank=True)

    def __str__(self) -> str:
        return f"{self.label} ({self.status})"


class Suggestion(models.Model):
    class Confidence(models.TextChoices):
        HIGH = "high"
        MEDIUM = "medium"
        LOW = "low"

    run = models.ForeignKey(Run, on_delete=models.CASCADE, related_name="suggestions")
    condition = models.ForeignKey(
        Condition, null=True, blank=True, on_delete=models.SET_NULL, related_name="suggestions"
    )
    display_code = models.CharField(max_length=8)
    description = models.TextField()
    hcc_number = models.PositiveIntegerField(null=True, blank=True)
    hcc_label = models.CharField(max_length=200, blank=True)
    # The merged evidence shown on the card (a suggestion may combine quotes
    # from several conditions, so it carries its own copy).
    evidence = models.JSONField(default=list, blank=True)
    meat = models.JSONField(default=list, blank=True)
    confidence = models.CharField(max_length=6, choices=Confidence.choices)
    confidence_reasons = models.JSONField(default=list, blank=True)
    rationale = models.TextField(blank=True)
    flags = models.JSONField(default=list, blank=True)
    candidate_rank = models.PositiveIntegerField()

    def __str__(self) -> str:
        return f"{self.display_code} ({self.confidence})"
