import pytest
from django.core.cache import cache
from django.test import Client

from apps.accounts.models import User


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    # The locmem cache (login rate limiting) survives across tests otherwise.
    cache.clear()


@pytest.fixture
def user(db: None) -> User:
    return User.objects.create_user(username="coder1", password="pw", role=User.Role.CODER)


@pytest.fixture
def admin_user(db: None) -> User:
    return User.objects.create_user(
        username="admin1", password="pw", role=User.Role.ADMIN, is_staff=True
    )


@pytest.fixture
def client(user: User) -> Client:
    """A logged-in coder client; the API requires a session everywhere."""
    logged_in = Client()
    logged_in.force_login(user)
    return logged_in


@pytest.fixture
def anon_client() -> Client:
    return Client()
