"""Role and identity helpers used by API endpoints (one place for checks)."""

from django.http import HttpRequest

from apps.accounts.models import User


def current_user(request: HttpRequest) -> User:
    """The session-authenticated user Ninja attached to the request."""
    user = getattr(request, "auth", None)
    assert isinstance(user, User), "endpoint must require authentication"
    return user


def is_admin(request: HttpRequest) -> bool:
    return current_user(request).role == User.Role.ADMIN
