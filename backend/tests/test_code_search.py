import pytest

from apps.reference.services import PostgresCodeRepository
from tests.test_loaders import load_fixture_code_set, load_fixture_hcc_map


@pytest.fixture
def repo(db: None) -> PostgresCodeRepository:
    load_fixture_code_set()
    load_fixture_hcc_map()
    return PostgresCodeRepository()


@pytest.mark.django_db
class TestCodeSearch:
    def test_specific_combination_code_ranks_first(self, repo: PostgresCodeRepository) -> None:
        hits = repo.search("type 2 diabetes chronic kidney disease", limit=5)
        assert hits, "expected results"
        assert hits[0].display_code == "E11.22"
        assert hits[0].rank == 1

    def test_billable_only_excludes_headers(self, repo: PostgresCodeRepository) -> None:
        hits = repo.search("chronic kidney disease", limit=10)
        codes = {hit.display_code for hit in hits}
        assert "N18" not in codes
        assert "N18.31" in codes

    def test_trigram_fallback_catches_typo(self, repo: PostgresCodeRepository) -> None:
        hits = repo.search("hypertenson", limit=5)  # misspelled: FTS alone finds nothing
        assert any(hit.display_code == "I10" for hit in hits)

    def test_limit_respected(self, repo: PostgresCodeRepository) -> None:
        assert len(repo.search("disease", limit=3)) <= 3

    def test_empty_query_returns_nothing(self, repo: PostgresCodeRepository) -> None:
        assert repo.search("   ") == []

    def test_hits_carry_hcc(self, repo: PostgresCodeRepository) -> None:
        hits = repo.search("type 2 diabetes chronic kidney disease", limit=5)
        top = hits[0]
        assert top.hcc_number == 37
        assert top.hcc_label == "Diabetes with Chronic Complications"


@pytest.mark.django_db
class TestLookups:
    def test_get_accepts_dotted_and_dotless(self, repo: PostgresCodeRepository) -> None:
        assert repo.get("E11.22") is not None
        assert repo.get("e1122") is not None
        assert repo.get("X99.99") is None

    def test_billable_in_category(self, repo: PostgresCodeRepository) -> None:
        codes = {c.code for c in repo.billable_in_category("E11")}
        assert codes == {"E1121", "E1122", "E1129", "E119"}

    def test_requires_active_code_set(self, db: None) -> None:
        with pytest.raises(ValueError, match="active"):
            PostgresCodeRepository()
