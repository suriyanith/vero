import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user, created before the first migration (swapping later is painful).

    Coders review runs; admins additionally manage users, label gold data in
    the Django admin, and see evaluation results.
    """

    class Role(models.TextChoices):
        CODER = "coder", "Coder"
        ADMIN = "admin", "Admin"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.CODER)
    display_name = models.CharField(max_length=150, blank=True)

    @property
    def is_admin_role(self) -> bool:
        return self.role == self.Role.ADMIN
