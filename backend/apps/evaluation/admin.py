"""Labeling happens here: the Note admin grows inline editors for the answer
key plus a "Mark reviewed" action."""

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from apps.notes.admin import NoteAdmin
from apps.notes.models import Note

from .models import AuditCase, EvalRun, GoldLabel, GoldNonCode


class GoldLabelInline(admin.TabularInline[GoldLabel, Note]):
    model = GoldLabel
    extra = 1


class GoldNonCodeInline(admin.TabularInline[GoldNonCode, Note]):
    model = GoldNonCode
    extra = 1


class AuditCaseInline(admin.TabularInline[AuditCase, Note]):
    model = AuditCase
    extra = 0


admin.site.unregister(Note)


@admin.register(Note)
class LabeledNoteAdmin(NoteAdmin):
    inlines = [GoldLabelInline, GoldNonCodeInline, AuditCaseInline]
    actions = ["mark_reviewed"]
    list_display = (  # type: ignore[assignment]  # wider than the base admin
        "title",
        "source",
        "split",
        "label_count",
        "fully_reviewed",
        "created_at",
    )

    @admin.display(description="gold labels")
    def label_count(self, obj: Note) -> int:
        return obj.gold_labels.count()

    @admin.display(boolean=True, description="reviewed")
    def fully_reviewed(self, obj: Note) -> bool:
        labels = list(obj.gold_labels.all()) + list(obj.gold_non_codes.all())
        return bool(labels) and all(item.reviewed for item in labels)

    @admin.action(description="Mark all labels on selected notes as reviewed")
    def mark_reviewed(self, request: HttpRequest, queryset: QuerySet[Note]) -> None:
        notes = list(queryset)
        GoldLabel.objects.filter(note__in=notes).update(reviewed=True)
        GoldNonCode.objects.filter(note__in=notes).update(reviewed=True)
        AuditCase.objects.filter(note__in=notes).update(reviewed=True)
        self.message_user(request, f"Marked labels on {len(notes)} note(s) as reviewed.")


@admin.register(EvalRun)
class EvalRunAdmin(admin.ModelAdmin[EvalRun]):
    list_display = ("created_at", "mode", "split", "model_name", "provisional")

    def has_add_permission(self, request: object) -> bool:
        return False

    def has_change_permission(self, request: object, obj: EvalRun | None = None) -> bool:
        return False
