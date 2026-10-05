import uuid

from django.conf import settings
from django.db import models

from apps.notes.models import Note


class GoldLabel(models.Model):
    """A human-verified correct code for a note. Generated drafts start with
    reviewed=False and are never treated as correct until a person reviews
    them."""

    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="gold_labels")
    display_code = models.CharField(max_length=8)
    rationale = models.TextField(blank=True)
    labeled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    reviewed = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["note", "display_code"], name="uniq_gold_label"),
        ]

    def __str__(self) -> str:
        return f"{self.display_code} on {self.note}"


class GoldNonCode(models.Model):
    """A condition that should NOT be coded, so hard-case accuracy can be
    measured per documentation pattern."""

    class Reason(models.TextChoices):
        HISTORICAL = "historical"
        RESOLVED = "resolved"
        UNCERTAIN = "uncertain"
        NEGATED = "negated"
        FAMILY_HISTORY = "family_history"
        NO_MEAT = "no_meat"

    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="gold_non_codes")
    condition_label = models.CharField(max_length=300)
    reason = models.CharField(max_length=15, choices=Reason.choices)
    rationale = models.TextField(blank=True)
    reviewed = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"not coded: {self.condition_label} ({self.reason})"


class AuditCase(models.Model):
    """A submitted-codes scenario with the verdict each code should receive."""

    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="audit_cases")
    submitted_codes = models.JSONField(default=list)
    expected_verdicts = models.JSONField(default=dict)  # {display_code: verdict}
    reviewed = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"audit case on {self.note} ({len(self.submitted_codes)} codes)"


class EvalRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    split = models.CharField(max_length=5)
    mode = models.CharField(max_length=10)  # coding | audit | both
    pipeline_version = models.CharField(max_length=20)
    prompt_versions = models.JSONField(default=dict)
    model_name = models.CharField(max_length=100)
    git_sha = models.CharField(max_length=40, blank=True)
    provisional = models.BooleanField(default=False)  # ran with unreviewed labels
    metrics = models.JSONField(default=dict)
    per_note_results = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"eval {self.mode} on {self.split} ({self.created_at:%Y-%m-%d %H:%M})"
