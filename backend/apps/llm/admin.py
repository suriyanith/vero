from django.contrib import admin

from .models import LlmCache, LlmCall


@admin.register(LlmCall)
class LlmCallAdmin(admin.ModelAdmin[LlmCall]):
    list_display = (
        "created_at",
        "step",
        "status",
        "cache_hit",
        "input_tokens",
        "output_tokens",
        "latency_ms",
        "model_name",
    )
    list_filter = ("step", "status", "cache_hit")

    def has_add_permission(self, request: object) -> bool:
        return False

    def has_change_permission(self, request: object, obj: LlmCall | None = None) -> bool:
        return False


@admin.register(LlmCache)
class LlmCacheAdmin(admin.ModelAdmin[LlmCache]):
    list_display = ("created_at", "model_name", "prompt_version", "request_hash")

    def has_add_permission(self, request: object) -> bool:
        return False

    def has_change_permission(self, request: object, obj: LlmCache | None = None) -> bool:
        return False
