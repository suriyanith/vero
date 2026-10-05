from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models


class CodeSetVersion(models.Model):
    """One loaded release of a code system, e.g. ICD-10-CM FY2027."""

    system = models.CharField(max_length=20, default="ICD10CM")
    fiscal_year = models.PositiveIntegerField()
    effective_from = models.DateField()
    source_url = models.URLField()
    sha256 = models.CharField(max_length=64)
    loaded_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["system", "fiscal_year"], name="uniq_system_fy"),
        ]

    def __str__(self) -> str:
        active = " (active)" if self.is_active else ""
        return f"{self.system} FY{self.fiscal_year}{active}"


class Icd10Code(models.Model):
    """One row of the CMS order file, enriched with tabular-list notes.

    `code` is stored without the dot for indexing (`E1122`); `display_code`
    keeps the dot (`E11.22`) and is what the API and UI always show.
    `notes` holds the structured tabular conventions for this code, with
    notes written on ancestor categories copied down at load time (ADR 0004):
    inclusion_terms, excludes1, excludes2, code_first, use_additional, and a
    `*_codes` list of the ICD-10 code patterns referenced by each note type.
    """

    code_set = models.ForeignKey(CodeSetVersion, on_delete=models.CASCADE, related_name="codes")
    code = models.CharField(max_length=7)
    display_code = models.CharField(max_length=8)
    short_desc = models.CharField(max_length=60)
    long_desc = models.TextField()
    is_billable = models.BooleanField()
    category = models.CharField(max_length=3)
    parent_code = models.CharField(max_length=7, blank=True)
    notes = models.JSONField(default=dict, blank=True)
    search_vector = SearchVectorField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["code_set", "code"], name="uniq_codeset_code"),
        ]
        indexes = [
            models.Index(fields=["code_set", "category"]),
            models.Index(fields=["code_set", "is_billable"]),
            GinIndex(fields=["search_vector"], name="icd10_search_vector_gin"),
        ]

    def __str__(self) -> str:
        return f"{self.display_code} {self.short_desc}"


class HccModel(models.Model):
    """One loaded risk adjustment model release, e.g. CMS-HCC V28 PY2027."""

    name = models.CharField(max_length=20, default="CMS-HCC")
    version = models.CharField(max_length=10)
    payment_year = models.PositiveIntegerField()
    source_url = models.URLField()
    sha256 = models.CharField(max_length=64)
    is_active = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "version", "payment_year"], name="uniq_hcc_model"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} {self.version} PY{self.payment_year}"


class HccCategory(models.Model):
    model = models.ForeignKey(HccModel, on_delete=models.CASCADE, related_name="categories")
    number = models.PositiveIntegerField()
    label = models.CharField(max_length=200)

    class Meta:
        verbose_name_plural = "HCC categories"
        constraints = [
            models.UniqueConstraint(fields=["model", "number"], name="uniq_hcc_number"),
        ]

    def __str__(self) -> str:
        return f"HCC {self.number}: {self.label}"


class Icd10HccMap(models.Model):
    model = models.ForeignKey(HccModel, on_delete=models.CASCADE, related_name="mappings")
    code_set = models.ForeignKey(CodeSetVersion, on_delete=models.CASCADE)
    code = models.CharField(max_length=7)
    hcc = models.ForeignKey(HccCategory, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["model", "code", "hcc"], name="uniq_code_hcc"),
        ]
        indexes = [models.Index(fields=["code_set", "code"])]

    def __str__(self) -> str:
        return f"{self.code} → HCC {self.hcc.number}"
