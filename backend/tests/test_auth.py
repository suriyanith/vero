import pytest
from django.test import Client

from apps.accounts.models import User


@pytest.mark.django_db
class TestAuthRequired:
    def test_api_requires_login(self, anon_client: Client) -> None:
        assert anon_client.get("/api/runs").status_code == 401
        assert anon_client.get("/api/codes/search?q=diabetes").status_code == 401
        assert anon_client.get("/api/auth/me").status_code == 401

    def test_health_is_public(self, anon_client: Client) -> None:
        assert anon_client.get("/api/health").status_code in (200, 503)


@pytest.mark.django_db
class TestCsrf:
    def test_post_without_csrf_token_rejected(self, user: User) -> None:
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(user)
        response = strict.post("/api/runs", {"text": "a note"}, content_type="application/json")
        assert response.status_code == 403

    def test_login_without_csrf_token_rejected(self, user: User) -> None:
        strict = Client(enforce_csrf_checks=True)
        response = strict.post(
            "/api/auth/login",
            {"username": "coder1", "password": "pw"},
            content_type="application/json",
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "CSRF_FAILED"

    def test_login_with_csrf_token_works(self, user: User) -> None:
        strict = Client(enforce_csrf_checks=True)
        strict.get("/api/auth/csrf")
        token = strict.cookies["csrftoken"].value
        response = strict.post(
            "/api/auth/login",
            {"username": "coder1", "password": "pw"},
            content_type="application/json",
            headers={"X-CSRFToken": token},
        )
        assert response.status_code == 200
        assert response.json()["role"] == "coder"


@pytest.mark.django_db
class TestLoginFlow:
    def test_wrong_password_then_me_unauthorized(self, user: User, anon_client: Client) -> None:
        response = anon_client.post(
            "/api/auth/login",
            {"username": "coder1", "password": "nope"},
            content_type="application/json",
        )
        assert response.status_code == 401
        assert anon_client.get("/api/auth/me").status_code == 401

    def test_rate_limit_after_five_attempts(self, user: User, anon_client: Client) -> None:
        for _ in range(5):
            anon_client.post(
                "/api/auth/login",
                {"username": "coder1", "password": "nope"},
                content_type="application/json",
            )
        response = anon_client.post(
            "/api/auth/login",
            {"username": "coder1", "password": "pw"},  # even the right password
            content_type="application/json",
        )
        assert response.status_code == 429

    def test_login_logout_me(self, user: User, anon_client: Client) -> None:
        anon_client.post(
            "/api/auth/login",
            {"username": "coder1", "password": "pw"},
            content_type="application/json",
        )
        me = anon_client.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["username"] == "coder1"
        anon_client.post("/api/auth/logout")
        assert anon_client.get("/api/auth/me").status_code == 401


@pytest.mark.django_db
class TestSeedUsers:
    def test_seed_users_creates_both_roles(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from django.core.management import call_command

        monkeypatch.setenv("VERO_SEED_CODER_PASSWORD", "coder-pw")
        monkeypatch.setenv("VERO_SEED_ADMIN_PASSWORD", "admin-pw")
        call_command("seed_users")
        call_command("seed_users")  # idempotent
        assert User.objects.count() == 2
        admin = User.objects.get(username="admin")
        assert admin.is_staff and admin.role == User.Role.ADMIN
        assert admin.check_password("admin-pw")

    def test_seed_users_requires_passwords(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from django.core.management import CommandError, call_command

        monkeypatch.delenv("VERO_SEED_CODER_PASSWORD", raising=False)
        monkeypatch.delenv("VERO_SEED_ADMIN_PASSWORD", raising=False)
        with pytest.raises(CommandError):
            call_command("seed_users")
