from django.contrib import admin

from .models import CodeSetVersion, HccCategory, HccModel, Icd10Code, Icd10HccMap


@admin.register(CodeSetVersion)
class CodeSetVersionAdmin(admin.ModelAdmin[CodeSetVersion]):
    list_display = ("system", "fiscal_year", "is_active", "loaded_at")
    readonly_fields = ("loaded_at",)


@admin.register(Icd10Code)
class Icd10CodeAdmin(admin.ModelAdmin[Icd10Code]):
    list_display = ("display_code", "short_desc", "is_billable", "category")
    list_filter = ("is_billable", "code_set")
    search_fields = ("code", "display_code", "long_desc")

    # Reference data is loaded by command, never edited by hand.
    def has_add_permission(self, request: object) -> bool:
        return False

    def has_change_permission(self, request: object, obj: Icd10Code | None = None) -> bool:
        return False

    def has_delete_permission(self, request: object, obj: Icd10Code | None = None) -> bool:
        return False


@admin.register(HccModel)
class HccModelAdmin(admin.ModelAdmin[HccModel]):
    list_display = ("name", "version", "payment_year", "is_active")


@admin.register(HccCategory)
class HccCategoryAdmin(admin.ModelAdmin[HccCategory]):
    list_display = ("number", "label", "model")
    list_filter = ("model",)
    search_fields = ("label",)


@admin.register(Icd10HccMap)
class Icd10HccMapAdmin(admin.ModelAdmin[Icd10HccMap]):
    list_display = ("code", "hcc", "model")
    search_fields = ("code",)
    list_filter = ("model",)
