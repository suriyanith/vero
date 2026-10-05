from tests.vero_core.builders import candidate, condition
from vero_core.fake_repo import FakeCodeRepository
from vero_core.interfaces import PipelineConfig
from vero_core.schemas import Candidate
from vero_core.steps.retrieve import build_query, retrieve_candidates


def repo_with(*candidates: Candidate) -> FakeCodeRepository:
    return FakeCodeRepository(candidates=list(candidates))


class TestBuildQuery:
    def test_includes_label_and_specificity(self) -> None:
        c = condition(label="type 2 diabetes", specificity_details=["with CKD", "stage 3a"])
        assert build_query(c) == "type 2 diabetes with CKD stage 3a"


class TestRetrieveCandidates:
    def test_category_expansion_adds_siblings_with_inherited_rank(self) -> None:
        repo = repo_with(
            candidate("E11.9", "Type 2 diabetes mellitus without complications"),
            candidate("E11.22", "Type 2 diabetes mellitus with diabetic chronic kidney disease"),
            candidate("E11.21", "Type 2 diabetes mellitus with diabetic nephropathy"),
            candidate("I10", "Essential hypertension"),
        )
        config = PipelineConfig(retrieval_top_k=1, category_expansion_top=1)
        results = retrieve_candidates(condition(label="type 2 diabetes mellitus"), repo, config)

        codes = {c.display_code for c in results}
        # Search returned one E11 code; its whole billable category came along.
        assert {"E11.9", "E11.22", "E11.21"} <= codes
        assert "I10" not in codes
        top_rank = min(c.rank for c in results)
        expanded = [c for c in results if c.display_code != results[0].display_code]
        assert all(c.rank == top_rank for c in expanded)

    def test_cap_on_candidates_per_condition(self) -> None:
        siblings = [
            candidate(f"J44.{i}", f"COPD variant {i} obstructive pulmonary") for i in range(9)
        ]
        repo = repo_with(*siblings)
        config = PipelineConfig(retrieval_top_k=2, max_candidates_per_condition=5)
        results = retrieve_candidates(condition(label="obstructive pulmonary COPD"), repo, config)
        assert len(results) == 5

    def test_non_billable_codes_never_retrieved(self) -> None:
        repo = repo_with(
            candidate("N18", "Chronic kidney disease", is_billable=False),
            candidate("N18.31", "Chronic kidney disease, stage 3a"),
        )
        results = retrieve_candidates(
            condition(label="chronic kidney disease"), repo, PipelineConfig()
        )
        assert all(c.is_billable for c in results)
        # expansion must not sneak the non-billable header back in
        assert "N18" not in {c.display_code for c in results}
