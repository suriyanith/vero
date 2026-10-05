"""Create one coder and one admin for local demos.

Passwords come from VERO_SEED_CODER_PASSWORD / VERO_SEED_ADMIN_PASSWORD —
never from code. Rerunning updates the passwords, nothing else.
"""

import os
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Seed a coder and an admin account from environment passwords"

    def handle(self, *args: Any, **options: Any) -> None:
        coder_password = os.environ.get("VERO_SEED_CODER_PASSWORD", "")
        admin_password = os.environ.get("VERO_SEED_ADMIN_PASSWORD", "")
        if not coder_password or not admin_password:
            raise CommandError(
                "Set VERO_SEED_CODER_PASSWORD and VERO_SEED_ADMIN_PASSWORD in the environment."
            )

        coder, _ = User.objects.update_or_create(
            username="coder",
            defaults={"role": User.Role.CODER, "display_name": "Demo Coder"},
        )
        coder.set_password(coder_password)
        coder.save()

        admin, _ = User.objects.update_or_create(
            username="admin",
            defaults={
                "role": User.Role.ADMIN,
                "display_name": "Demo Admin",
                "is_staff": True,  # Django admin access (labeling, data management)
                "is_superuser": True,
            },
        )
        admin.set_password(admin_password)
        admin.save()

        self.stdout.write(self.style.SUCCESS("Seeded users: coder, admin"))
