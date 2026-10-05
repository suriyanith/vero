import uuid
from typing import Any

from django.conf import settings
from django.db import models

from apps.runs.models import AuditFinding, Run, Suggestion


class AppendOnlyError(Exception):
    """Raised on any attempt to change or delete a review decision."""


class ReviewDecision(models.Model):
    """One reviewer decision. Append-only: an audit trail you can edit isn't one.

    The newest decision for a suggestion is the current one; changing your
    mind means appending another row. `evidence_snapshot` freezes exactly
    what the reviewer saw (quotes, MEAT, confidence, rationale), so the
    decision stays self-contained even if prompts or code data change later.
    """

    class Action(models.TextChoices):
        ACCEPT = "accept"
        REJECT = "reject"
        MODIFY = "modify"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(Run, on_delete=models.PROTECT, related_name="decisions")
    suggestion = models.ForeignKey(
        Suggestion, null=True, blank=True, on_delete=models.PROTECT, related_name="decisions"
    )
    finding = models.ForeignKey(
        AuditFinding, null=True, blank=True, on_delete=models.PROTECT, related_name="decisions"
    )
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=10, choices=Action.choices)
    original_code = models.CharField(max_length=8)
    final_code = models.CharField(max_length=8, blank=True)
    reason = models.TextField(blank=True)
    evidence_snapshot = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["run", "created_at"])]

    def __str__(self) -> str:
        return f"{self.action} {self.original_code} by {self.reviewer}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise AppendOnlyError("Review decisions cannot be modified; append a new one.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> Any:
        raise AppendOnlyError("Review decisions cannot be deleted.")
