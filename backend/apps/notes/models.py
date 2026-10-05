import uuid

from django.conf import settings
from django.db import models


class Mode(models.TextChoices):
    CODING = "coding"
    AUDIT = "audit"


class Batch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    mode = models.CharField(max_length=10, choices=Mode.choices)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "batches"

    def __str__(self) -> str:
        return self.name


class Note(models.Model):
    class Source(models.TextChoices):
        SAMPLE = "sample"
        USER = "user"

    class Split(models.TextChoices):
        NONE = "none"
        DEV = "dev"
        TEST = "test"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    text = models.TextField()
    text_sha256 = models.CharField(max_length=64)
    source = models.CharField(max_length=10, choices=Source.choices)
    batch = models.ForeignKey(Batch, null=True, blank=True, on_delete=models.SET_NULL)
    split = models.CharField(max_length=5, choices=Split.choices, default=Split.NONE)
    scenario_tags = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.title
