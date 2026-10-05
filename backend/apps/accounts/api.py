from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.http import HttpRequest
from django.middleware.csrf import get_token
from ninja import Router, Schema
from ninja.responses import Status
from ninja.utils import check_csrf

from apps.accounts.auth import current_user
from apps.accounts.models import User

router = Router(tags=["auth"])

LOGIN_ATTEMPT_LIMIT = 5
LOGIN_ATTEMPT_WINDOW_SECONDS = 60


class LoginIn(Schema):
    username: str
    password: str


class UserOut(Schema):
    username: str
    display_name: str
    role: str


class ErrorOut(Schema):
    error: dict[str, str]


class OkOut(Schema):
    ok: bool


def _error(code: str, message: str) -> dict[str, dict[str, str]]:
    return {"error": {"code": code, "message": message}}


@router.get("/auth/csrf", response=OkOut, auth=None)
def csrf(request: HttpRequest) -> OkOut:
    # Calling get_token marks the response so CsrfViewMiddleware sets the
    # csrftoken cookie (ensure_csrf_cookie cannot wrap schema-returning views).
    get_token(request)
    return OkOut(ok=True)


@router.post(
    "/auth/login", response={200: UserOut, 401: ErrorOut, 403: ErrorOut, 429: ErrorOut}, auth=None
)
def login_view(request: HttpRequest, payload: LoginIn) -> Status[object]:
    # auth=None skips Ninja's CSRF check, so enforce it explicitly here.
    csrf_error = check_csrf(request)
    if csrf_error is not None:
        return Status(403, _error("CSRF_FAILED", "Missing or invalid CSRF token."))

    attempts_key = f"login_attempts:{payload.username.lower()}"
    attempts = cache.get(attempts_key, 0)
    if attempts >= LOGIN_ATTEMPT_LIMIT:
        return Status(429, _error("TOO_MANY_ATTEMPTS", "Too many login attempts. Wait a minute."))

    user = authenticate(request, username=payload.username, password=payload.password)
    if user is None:
        cache.set(attempts_key, attempts + 1, LOGIN_ATTEMPT_WINDOW_SECONDS)
        return Status(401, _error("INVALID_CREDENTIALS", "Wrong username or password."))

    cache.delete(attempts_key)
    login(request, user)
    assert isinstance(user, User)
    return Status(
        200, UserOut(username=user.username, display_name=user.display_name, role=user.role)
    )


@router.post("/auth/logout", response=OkOut)
def logout_view(request: HttpRequest) -> OkOut:
    logout(request)
    return OkOut(ok=True)


@router.get("/auth/me", response=UserOut)
def me(request: HttpRequest) -> UserOut:
    user = current_user(request)
    return UserOut(username=user.username, display_name=user.display_name, role=user.role)
