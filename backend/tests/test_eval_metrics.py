from apps.evaluation.metrics import (
    AuditCaseResult,
    CodingNoteResult,
    audit_metrics,
    coding_metrics,
    operational_metrics,
    precision_recall_f1,
)


class TestPrecisionRecallF1:
    def test_perfect(self) -> None:
        scores = precision_recall_f1({"A", "B"}, {"A", "B"})
        assert scores == {"precision": 1.0, "recall": 1.0, "f1": 1.0}

    def test_partial(self) -> None:
        # predicted {A, C} vs gold {A, B}: P=1/2, R=1/2, F1=1/2
        scores = precision_recall_f1({"A", "C"}, {"A", "B"})
        assert scores["precision"] == 0.5
        assert scores["recall"] == 0.5
        assert scores["f1"] == 0.5

    def test_empty_sets_give_none(self) -> None:
        assert precision_recall_f1(set(), {"A"})["precision"] is None
        assert precision_recall_f1({"A"}, set())["recall"] is None


def result(**overrides: object) -> CodingNoteResult:
    defaults: dict[str, object] = dict(
        note_title="n1",
        suggestions=[("E11.22", "high", 37), ("N18.31", "high", 329)],
        gold_codes={"E11.22", "N18.31"},
        gold_hccs={37, 329},
        gold_non_codes=[],
        suggestion_condition_labels=["type 2 diabetes with CKD", "CKD stage 3a"],
        dropped_quotes=0,
        duration_ms=1000,
        total_tokens=500,
    )
    defaults.update(overrides)
    return CodingNoteResult(**defaults)  # type: ignore[arg-type]


class TestCodingMetrics:
    def test_exact_match_scores_perfectly(self) -> None:
        metrics = coding_metrics([result()])
        assert metrics["code_level"]["f1"] == 1.0  # type: ignore[index]  # noqa
        assert metrics["hcc_level"]["recall"] == 1.0  # type: ignore[index]

    def test_category_partial_credit(self) -> None:
        # Predicted E11.21 instead of E11.22: wrong code, right category.
        metrics = coding_metrics(
            [result(suggestions=[("E11.21", "high", 37)], gold_codes={"E11.22"}, gold_hccs={37})]
        )
        assert metrics["code_level"]["precision"] == 0.0  # type: ignore[index]
        assert metrics["category_level"]["precision"] == 1.0  # type: ignore[index]
        assert metrics["hcc_level"]["precision"] == 1.0  # type: ignore[index]

    def test_accuracy_by_confidence(self) -> None:
        metrics = coding_metrics(
            [
                result(
                    suggestions=[("E11.22", "high", 37), ("I10", "low", None)],
                    gold_codes={"E11.22"},
                    gold_hccs={37},
                )
            ]
        )
        by_confidence = metrics["accuracy_by_confidence"]
        assert by_confidence["high"] == 1.0  # type: ignore[index]
        assert by_confidence["low"] == 0.0  # type: ignore[index]
        assert by_confidence["medium"] is None  # type: ignore[index]

    def test_hard_cases_track_violations_per_reason(self) -> None:
        metrics = coding_metrics(
            [
                result(
                    gold_non_codes=[
                        ("heart failure", "uncertain"),  # violated: suggested below
                        ("colon cancer", "historical"),  # respected
                    ],
                    suggestions=[("I50.9", "low", 226)],
                    suggestion_condition_labels=["heart failure"],
                    gold_codes=set(),
                    gold_hccs=set(),
                )
            ]
        )
        hard = metrics["hard_cases"]
        assert hard["uncertain"]["accuracy"] == 0.0  # type: ignore[index]
        assert hard["historical"]["accuracy"] == 1.0  # type: ignore[index]

    def test_evidence_integrity_sums(self) -> None:
        metrics = coding_metrics(
            [result(dropped_quotes=2), result(note_title="n2", dropped_quotes=1)]
        )
        integrity = metrics["evidence_integrity"]
        assert integrity["dropped_quotes"] == 3  # type: ignore[index]
        assert integrity["unverified_quotes_shown"] == 0  # type: ignore[index]


class TestAuditMetrics:
    def test_accuracy_confusion_and_rates(self) -> None:
        results = [
            AuditCaseResult(
                note_title="n1",
                verdicts={
                    "E11.9": ("SPECIFICITY_MISMATCH", "SPECIFICITY_MISMATCH"),
                    "N18.31": ("SUPPORTED", "SUPPORTED"),
                    "I50.9": ("NOT_SUPPORTED", "SUPPORTED"),  # missed an unsupported code
                    "C18.9": ("NOT_SUPPORTED", "NOT_SUPPORTED"),
                },
            )
        ]
        metrics = audit_metrics(results)
        assert metrics["overall_accuracy"] == 0.75
        assert metrics["per_verdict_accuracy"]["NOT_SUPPORTED"] == 0.5  # type: ignore[index]
        assert metrics["confusion"]["NOT_SUPPORTED->SUPPORTED"] == 1  # type: ignore[index]
        assert metrics["unsupported_caught_rate"] == 0.5
        assert metrics["supported_wrongly_flagged_rate"] == 0.0


class TestOperationalMetrics:
    def test_success_rate_and_durations(self) -> None:
        metrics = operational_metrics(
            [
                result(duration_ms=1000, total_tokens=400),
                result(note_title="n2", duration_ms=3000, total_tokens=600),
                result(note_title="n3", failed=True),
            ]
        )
        assert metrics["notes_attempted"] == 3
        assert metrics["success_rate"] == 2 / 3
        assert metrics["average_duration_ms"] == 2000
        assert metrics["slowest_duration_ms"] == 3000
        assert metrics["average_tokens"] == 500
