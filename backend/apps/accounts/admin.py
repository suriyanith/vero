from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class VeroUserAdmin(UserAdmin[User]):
    fieldsets = (*(UserAdmin.fieldsets or ()), ("Vero", {"fields": ("role", "display_name")}))
    list_display = ("username", "display_name", "role", "is_active")
    list_filter = ("role", "is_active")
