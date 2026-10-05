from tests.vero_core.builders import candidate, condition, quote, selection
from vero_core.fake_llm import FakeLLMClient
from vero_core.fake_repo import FakeCodeRepository
from vero_core.interfaces import PipelineConfig, PipelineDeps
from vero_core.schemas import SelectionResult
from vero_core.steps.select import build_conditions_block, select_codes


def deps_returning(result: SelectionResult) -> PipelineDeps:
    return PipelineDeps(
        llm=FakeLLMClient(responses={"select": result}),
        codes=FakeCodeRepository(candidates=[]),
    )


class TestConditionsBlock:
    def test_numbering_evidence_and_candidate_notes(self) -> None:
        conditions = [
            condition(label="CHF", quotes=[quote(text="CHF stable on furosemide")]),
            condition(label="COPD", specificity_details=["mild"]),
        ]
        candidates = [
            [
                candidate(
                    "I50.9",
                    "Heart failure, unspecified",
                    notes={"excludes1": ["neonatal cardiac failure (P29.0)"]},
                )
            ],
            [candidate("J44.9", "Chronic obstructive pulmonary disease, unspecified")],
        ]
        block = build_conditions_block(conditions, candidates)
        assert "Condition 1: CHF" in block
        assert "Condition 2: COPD" in block
        assert '"CHF stable on furosemide"' in block
        assert "1. I50.9 — Heart failure, unspecified" in block
        assert "Excludes1: neonatal cardiac failure (P29.0)" in block
        assert "Specificity details: mild" in block


class TestSelectCodes:
    def test_code_outside_candidate_list_is_discarded(self) -> None:
        conditions = [condition(label="diabetes")]
        candidates = [[candidate("E11.9", "Type 2 diabetes mellitus without complications")]]
        # The model picked one allowed code and one it made up.
        result = SelectionResult(
            selections=[selection(1, codes=[("E11.9", "fits"), ("E99.99", "invented")])]
        )
        outcome = select_codes(conditions, candidates, deps_returning(result), PipelineConfig())
        assert [c.code for c in outcome.selections[1].codes] == ["E11.9"]
        assert outcome.out_of_candidates == [(1, "E99.99")]

    def test_hallucinated_or_duplicate_condition_index_ignored(self) -> None:
        conditions = [condition(label="diabetes")]
        candidates = [[candidate("E11.9")]]
        result = SelectionResult(
            selections=[
                selection(7, codes=[("E11.9", "wrong index")]),
                selection(1, codes=[("E11.9", "first")]),
                selection(1, codes=[("E11.9", "duplicate")]),
            ]
        )
        outcome = select_codes(conditions, candidates, deps_returning(result), PipelineConfig())
        assert list(outcome.selections) == [1]
        assert outcome.selections[1].codes[0].rationale == "first"

    def test_no_fit_selection_passes_through(self) -> None:
        conditions = [condition(label="vague complaint")]
        candidates = [[candidate("R53.1", "Weakness")]]
        result = SelectionResult(selections=[selection(1, codes=[], no_fit=True)])
        outcome = select_codes(conditions, candidates, deps_returning(result), PipelineConfig())
        assert outcome.selections[1].no_fit is True
