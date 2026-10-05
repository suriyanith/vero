import uuid

import pytest
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_user_model_is_custom_with_uuid_pk_and_role() -> None:
    user_model = get_user_model()
    assert user_model._meta.label == "accounts.User"

    user = user_model.objects.create_user(username="coder1", password="x")
    assert isinstance(user.id, uuid.UUID)
    assert user.role == user_model.Role.CODER
    assert not user.is_admin_role

    admin = user_model.objects.create_user(
        username="admin1", password="x", role=user_model.Role.ADMIN
    )
    assert admin.is_admin_role
