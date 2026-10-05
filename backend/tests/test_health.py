import pytest
from django.test import Client


@pytest.mark.django_db
def test_health_returns_ok(client: Client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] is True


@pytest.mark.django_db
def test_health_requires_no_auth(client: Client) -> None:
    # Health is one of the few endpoints that must work before login.
    response = client.get("/api/health")
    assert response.status_code == 200
