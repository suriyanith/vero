import pytest
from django.test import Client


@pytest.mark.django_db
def test_health_reports_database_but_fails_without_code_set(client: Client) -> None:
    # Health requires both a reachable database and an active code set;
    # test_codes_api covers the 200 path with data loaded.
    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "NO_CODE_SET"
