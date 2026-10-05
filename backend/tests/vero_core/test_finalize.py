from tests.vero_core.builders import candidate, condition, quote, selection
from vero_core.interfaces import PipelineConfig
from vero_core.schemas import (
    Candidate,
    Certainty,
    ConditionSelection,
    Confidence,
    Meat,
    Suggestion,
    VerifiedCondition,
)
from vero_core.steps.finalize import (
    FLAG_EXCLUDES1,
    FLAG_MISSING_ADDITIONAL,
    FLAG_NO_MEAT,
    FLAG_UNDERSPECIFIED,
    finalize,
)

CONFIG = PipelineConfig()

E1122 = candidate(
    "E11.22",
    "Type 2 diabetes mellitus with diabetic chronic kidney disease",
    notes={
        "excludes1_codes": ["E08", "E09", "E10", "E13"],
        "use_additional": [
            "code to identify control using insulin (Z79.4)",
            "code to identify stage of chronic kidney disease (N18.1-N18.6)",
        ],
    },
    hcc_number=37,
    hcc_label="Diabetes with Chronic Complications",
)
E109 = candidate(
    "E10.9",
    "Type 1 diabetes mellitus without complications",
    notes={"excludes1_codes": ["E11"]},
)
N1831 = candidate("N18.31", "Chronic kidney disease, stage 3a", hcc_number=329)


class TestReconcileRules:
    def test_excludes1_conflict_flags_both_directions(self) -> None:
        conditions = [condition(label="type 2 diabetes"), condition(label="type 1 diabetes")]
        suggestions, _ = finalize(
            conditions,
            {1: selection(1, codes=[("E11.22", "x")]), 2: selection(2, codes=[("E10.9", "y")])},
            [[E1122], [E109]],
            CONFIG,
        )
        by_code = {s.code: s for s in suggestions}
        assert FLAG_EXCLUDES1 in by_code["E11.22"].flags
        assert FLAG_EXCLUDES1 in by_code["E10.9"].flags
        assert all(s.confidence == Confidence.LOW for s in suggestions)

    def test_missing_additional_code_flagged_when_family_absent(self) -> None:
        suggestions, _ = finalize(
            [condition(label="type 2 diabetes with CKD")],
            {1: selection(1, codes=[("E11.22", "x")])},
            [[E1122]],
            CONFIG,
        )
        assert FLAG_MISSING_ADDITIONAL in suggestions[0].flags

    def test_missing_additional_satisfied_by_companion_code(self) -> None:
        conditions = [condition(label="type 2 diabetes with CKD"), condition(label="CKD 3a")]
        suggestions, _ = finalize(
            conditions,
            {1: selection(1, codes=[("E11.22", "x")]), 2: selection(2, codes=[("N18.31", "y")])},
            [[E1122], [N1831]],
            CONFIG,
        )
        e1122 = next(s for s in suggestions if s.code == "E11.22")
        assert FLAG_MISSING_ADDITIONAL not in e1122.flags

    def test_z_code_only_notes_never_flag(self) -> None:
        n1831_with_z = N1831.model_copy(
            update={
                "notes": {"use_additional": ["code to identify kidney transplant status (Z94.0)"]}
            }
        )
        suggestions, _ = finalize(
            [condition(label="CKD 3a")],
            {1: selection(1, codes=[("N18.31", "x")])},
            [[n1831_with_z]],
            CONFIG,
        )
        assert FLAG_MISSING_ADDITIONAL not in suggestions[0].flags

    def test_possibly_underspecified(self) -> None:
        unspecified = candidate("I50.9", "Heart failure, unspecified")
        suggestions, _ = finalize(
            [condition(label="heart failure", specificity_details=["chronic systolic"])],
            {1: selection(1, codes=[("I50.9", "x")])},
            [[unspecified]],
            CONFIG,
        )
        assert FLAG_UNDERSPECIFIED in suggestions[0].flags

    def test_no_meat_flag(self) -> None:
        suggestions, _ = finalize(
            [condition(label="CKD", quotes=[quote(meat=[])])],
            {1: selection(1, codes=[("N18.31", "x")])},
            [[N1831]],
            CONFIG,
        )
        assert FLAG_NO_MEAT in suggestions[0].flags
        assert suggestions[0].confidence == Confidence.LOW


class TestConfidenceRules:
    def base(
        self,
        conditions: list[VerifiedCondition] | None = None,
        selections: dict[int, ConditionSelection] | None = None,
        candidates: list[list[Candidate]] | None = None,
    ) -> Suggestion:
        """One condition whose suggestion satisfies every High criterion."""
        suggestions, _ = finalize(
            conditions
            if conditions is not None
            else [condition(label="CKD 3a", quotes=[quote(meat=[Meat.EVALUATE])])],
            selections
            if selections is not None
            else {1: selection(1, codes=[("N18.31", "stage documented")])},
            candidates if candidates is not None else [[N1831]],
            CONFIG,
        )
        return suggestions[0]

    def test_high_when_everything_holds(self) -> None:
        suggestion = self.base()
        assert suggestion.confidence == Confidence.HIGH
        assert "no flags" in suggestion.confidence_reasons

    def test_medium_on_case_insensitive_match(self) -> None:
        s = self.base(
            conditions=[
                condition(
                    label="CKD 3a",
                    quotes=[quote(meat=[Meat.EVALUATE], match_type="case_insensitive")],
                )
            ]
        )
        assert s.confidence == Confidence.MEDIUM
        assert any("case-insensitively" in r for r in s.confidence_reasons)

    def test_medium_on_ambiguous_quote(self) -> None:
        s = self.base(
            conditions=[
                condition(label="CKD 3a", quotes=[quote(meat=[Meat.EVALUATE], ambiguous=True)])
            ]
        )
        assert s.confidence == Confidence.MEDIUM

    def test_medium_on_rank_between_4_and_10(self) -> None:
        s = self.base(candidates=[[N1831.model_copy(update={"rank": 7})]])
        assert s.confidence == Confidence.MEDIUM
        assert any("outside the top 3" in r for r in s.confidence_reasons)

    def test_medium_on_model_certainty_medium(self) -> None:
        s = self.base(
            selections={1: selection(1, codes=[("N18.31", "x")], certainty=Certainty.MEDIUM)}
        )
        assert s.confidence == Confidence.MEDIUM

    def test_medium_on_specificity_flag(self) -> None:
        s = self.base(
            selections={
                1: selection(1, codes=[("N18.31", "x")], specificity_flags=["stage not stated"])
            }
        )
        assert s.confidence == Confidence.MEDIUM

    def test_low_on_model_certainty_low(self) -> None:
        s = self.base(
            selections={1: selection(1, codes=[("N18.31", "x")], certainty=Certainty.LOW)}
        )
        assert s.confidence == Confidence.LOW

    def test_low_on_rank_beyond_10(self) -> None:
        s = self.base(candidates=[[N1831.model_copy(update={"rank": 11})]])
        assert s.confidence == Confidence.LOW


class TestDedupAndDrops:
    def test_same_code_from_two_conditions_merges(self) -> None:
        quote_a = quote(text="diabetes stable", start=0, end=15, meat=[Meat.ASSESS])
        quote_b = quote(text="continue metformin", start=20, end=38, meat=[Meat.TREAT])
        conditions = [
            condition(label="diabetes", quotes=[quote_a]),
            condition(label="DM follow-up", quotes=[quote_b]),
        ]
        suggestions, _ = finalize(
            conditions,
            {
                1: selection(1, codes=[("E11.22", "a")]),
                2: selection(2, codes=[("E11.22", "b")], certainty=Certainty.MEDIUM),
            },
            [[E1122], [E1122]],
            CONFIG,
        )
        [merged] = suggestions
        assert merged.condition_label == "diabetes + DM follow-up"
        assert len(merged.evidence) == 2
        assert merged.meat == [Meat.ASSESS, Meat.TREAT]

    def test_no_fit_and_missing_selection_recorded_as_dropped(self) -> None:
        conditions = [condition(label="vague"), condition(label="unanswered")]
        suggestions, dropped = finalize(
            conditions,
            {1: selection(1, codes=[], no_fit=True)},
            [[], []],
            CONFIG,
        )
        assert suggestions == []
        reasons = {d.label: d.reason for d in dropped}
        assert reasons == {"vague": "no_fit", "unanswered": "no_selection"}

    def test_hcc_carried_from_candidate(self) -> None:
        suggestions, _ = finalize(
            [condition(label="diabetes with CKD")],
            {1: selection(1, codes=[("E11.22", "x")])},
            [[E1122]],
            CONFIG,
        )
        assert suggestions[0].hcc_number == 37
        assert suggestions[0].hcc_label == "Diabetes with Chronic Complications"
