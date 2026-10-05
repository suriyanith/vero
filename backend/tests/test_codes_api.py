import pytest
from django.test import Client

from tests.test_loaders import load_fixture_code_set, load_fixture_hcc_map


@pytest.fixture
def loaded(db: None) -> None:
    load_fixture_code_set()
    load_fixture_hcc_map()


@pytest.mark.django_db
class TestCodesApi:
    def test_search_endpoint(self, loaded: None, client: Client) -> None:
        response = client.get("/api/codes/search", {"q": "type 2 diabetes chronic kidney"})
        assert response.status_code == 200
        body = response.json()
        assert body[0]["display_code"] == "E11.22"
        assert body[0]["hcc_number"] == 37

    def test_search_requires_query_param(self, loaded: None, client: Client) -> None:
        assert client.get("/api/codes/search").status_code == 422

    def test_code_detail(self, loaded: None, client: Client) -> None:
        response = client.get("/api/codes/E11.22")
        assert response.status_code == 200
        body = response.json()
        assert body["description"].startswith("Type 2 diabetes mellitus with diabetic chronic")
        assert body["is_billable"] is True
        assert body["hcc_label"] == "Diabetes with Chronic Complications"
        assert "use_additional" in body["notes"]

    def test_code_detail_unknown_404(self, loaded: None, client: Client) -> None:
        response = client.get("/api/codes/X99.99")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "CODE_NOT_FOUND"


@pytest.mark.django_db
class TestHealthWithCodeSet:
    def test_health_503_without_code_set(self, client: Client) -> None:
        response = client.get("/api/health")
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "NO_CODE_SET"

    def test_health_200_with_code_set(self, loaded: None, client: Client) -> None:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["code_set_loaded"] is True
