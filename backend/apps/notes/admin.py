from django.contrib import admin

from .models import Batch, Note


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin[Note]):
    list_display = ("title", "source", "split", "created_at")
    list_filter = ("source", "split")
    search_fields = ("title",)
    readonly_fields = ("text_sha256", "created_at")


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin[Batch]):
    list_display = ("name", "mode", "created_by", "created_at")
