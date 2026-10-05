from django.contrib import admin

from .models import ReviewDecision


@admin.register(ReviewDecision)
class ReviewDecisionAdmin(admin.ModelAdmin[ReviewDecision]):
    """Read-only: the append-only guarantee holds in the admin too."""

    list_display = ("created_at", "action", "original_code", "final_code", "reviewer", "run")
    list_filter = ("action",)
    search_fields = ("original_code", "final_code")

    def has_add_permission(self, request: object) -> bool:
        return False

    def has_change_permission(self, request: object, obj: ReviewDecision | None = None) -> bool:
        return False

    def has_delete_permission(self, request: object, obj: ReviewDecision | None = None) -> bool:
        return False
