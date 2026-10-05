from pathlib import Path

from tests.vero_core.builders import candidate, condition, quote
from vero_core.cli import build_fake_deps
from vero_core.fake_repo import FakeCodeRepository
from vero_core.interfaces import PipelineConfig
from vero_core.pipeline import audit_note
from vero_core.schemas import (
    AuditVerdict,
    CodingResult,
    ConditionStatus,
    Confidence,
    Meat,
    Suggestion,
    Usage,
    VerifiedCondition,
)
from vero_core.steps.audit import audit_findings, classify_submitted_code

FIXTURES = Path(__file__).resolve().parents[3] / "data" / "fixtures" / "appendix_c"

REPO = FakeCodeRepository(
    candidates=[
        candidate(
            "E11.22", "Type 2 diabetes mellitus with diabetic chronic kidney disease", hcc_number=37
        ),
        candidate("E11.9", "Type 2 diabetes mellitus without complications", hcc_number=38),
        candidate("N18.31", "Chronic kidney disease, stage 3a", hcc_number=329),
        candidate("I50.9", "Heart failure, unspecified", hcc_number=226),
        candidate("C18.9", "Malignant neoplasm of colon, unspecified", hcc_number=22),
        candidate("I10", "Essential (primary) hypertension"),
        candidate("N18", "Chronic kidney disease (CKD)", is_billable=False),
    ]
)


def suggestion(
    code: str,
    description: str = "desc",
    meat: list[Meat] | None = None,
    hcc_number: int | None = None,
) -> Suggestion:
    return Suggestion(
        code=code,
        description=description,
        hcc_number=hcc_number,
        hcc_label=None,
        condition_label="condition",
        evidence=[quote(text="supporting quote")],
        meat=meat if meat is not None else [Meat.ASSESS],
        confidence=Confidence.HIGH,
        confidence_reasons=[],
        candidate_rank=1,
        rationale="",
        flags=[] if meat is None or meat else ["no_meat"],
    )


def coding_result(
    suggestions: list[Suggestion] | None = None,
    not_coded: list[VerifiedCondition] | None = None,
) -> CodingResult:
    return CodingResult(
        conditions=[],
        suggestions=suggestions or [],
        not_coded=not_coded or [],
        dropped=[],
        usage=Usage(input_tokens=0, output_tokens=0, duration_ms=0, dropped_quotes=0),
    )


class TestVerdictLadder:
    def test_unknown_code_is_invalid(self) -> None:
        finding = classify_submitted_code("X99.99", coding_result(), REPO)
        assert finding.verdict == AuditVerdict.INVALID_CODE
        assert finding.submitted_code == "X99.99"

    def test_non_billable_header_is_invalid(self) -> None:
        finding = classify_submitted_code("N18", coding_result(), REPO)
        assert finding.verdict == AuditVerdict.INVALID_CODE

    def test_exact_match_with_meat_is_supported(self) -> None:
        coding = coding_result([suggestion("N18.31", meat=[Meat.EVALUATE])])
        finding = classify_submitted_code("N18.31", coding, REPO)
        assert finding.verdict == AuditVerdict.SUPPORTED
        assert finding.evidence[0].text == "supporting quote"

    def test_exact_match_without_meat_is_weak_support(self) -> None:
        coding = coding_result([suggestion("N18.31", meat=[])])
        finding = classify_submitted_code("N18.31", coding, REPO)
        assert finding.verdict == AuditVerdict.WEAK_SUPPORT
        assert finding.reason_code == "NO_MEAT"

    def test_same_category_different_code_is_specificity_mismatch(self) -> None:
        coding = coding_result([suggestion("E11.22", "the combination code")])
        finding = classify_submitted_code("E11.9", coding, REPO)
        assert finding.verdict == AuditVerdict.SPECIFICITY_MISMATCH
        assert finding.suggested_code == "E11.22"

    def test_same_hcc_different_category_is_specificity_mismatch(self) -> None:
        # Both map to HCC 329 in this fixture world but different categories.
        repo = FakeCodeRepository(
            candidates=[
                candidate("N18.31", "CKD stage 3a", hcc_number=329),
                candidate("Q61.2", "Polycystic kidney", hcc_number=329),
            ]
        )
        coding = coding_result([suggestion("N18.31", hcc_number=329)])
        finding = classify_submitted_code("Q61.2", coding, repo)
        assert finding.verdict == AuditVerdict.SPECIFICITY_MISMATCH

    def test_code_for_uncertain_condition_is_not_supported(self) -> None:
        not_coded = [
            condition(
                label="heart failure",
                status=ConditionStatus.UNCERTAIN,
                quotes=[quote(text="rule out heart failure")],
            )
        ]
        finding = classify_submitted_code("I50.9", coding_result(not_coded=not_coded), REPO)
        assert finding.verdict == AuditVerdict.NOT_SUPPORTED
        assert finding.reason_code == "UNCERTAIN"
        assert finding.evidence[0].text == "rule out heart failure"

    def test_code_for_historical_condition_is_not_supported(self) -> None:
        not_coded = [
            condition(
                label="colon cancer",
                status=ConditionStatus.HISTORICAL,
                quotes=[quote(text="History of colon cancer")],
            )
        ]
        finding = classify_submitted_code("C18.9", coding_result(not_coded=not_coded), REPO)
        assert finding.reason_code == "HISTORICAL"

    def test_unrelated_code_is_not_documented(self) -> None:
        finding = classify_submitted_code("I10", coding_result(), REPO)
        assert finding.verdict == AuditVerdict.NOT_SUPPORTED
        assert finding.reason_code == "NOT_DOCUMENTED"


class TestMissedHccsAndDedup:
    def test_documented_hcc_not_submitted_is_missed(self) -> None:
        coding = coding_result([suggestion("E11.22", hcc_number=37)])
        findings = audit_findings(["I10"], coding, REPO, PipelineConfig())
        missed = [f for f in findings if f.verdict == AuditVerdict.MISSED_HCC]
        assert len(missed) == 1
        assert missed[0].suggested_code == "E11.22"
        assert missed[0].submitted_code is None

    def test_no_missed_hcc_when_submitted_or_already_offered(self) -> None:
        coding = coding_result(
            [suggestion("E11.22", hcc_number=37), suggestion("N18.31", hcc_number=329)]
        )
        # E11.9 triggers a specificity mismatch offering E11.22; N18.31 submitted.
        findings = audit_findings(["E11.9", "N18.31"], coding, REPO, PipelineConfig())
        assert not [f for f in findings if f.verdict == AuditVerdict.MISSED_HCC]

    def test_non_hcc_suggestion_never_missed(self) -> None:
        coding = coding_result([suggestion("I10", hcc_number=None)])
        findings = audit_findings([], coding, REPO, PipelineConfig())
        assert findings == []

    def test_duplicate_submitted_codes_classified_once(self) -> None:
        coding = coding_result([suggestion("N18.31", meat=[Meat.EVALUATE], hcc_number=329)])
        findings = audit_findings(["N18.31", "n1831"], coding, REPO, PipelineConfig())
        assert len(findings) == 1


class TestAppendixCAuditExample:
    def test_expected_verdicts(self) -> None:
        note = (FIXTURES / "note.txt").read_text(encoding="utf-8")
        result = audit_note(
            note,
            ["E11.9", "N18.31", "I50.9", "C18.9"],
            build_fake_deps(FIXTURES),
            PipelineConfig(),
        )
        by_code = {f.submitted_code: f for f in result.findings if f.submitted_code}

        assert by_code["E11.9"].verdict == AuditVerdict.SPECIFICITY_MISMATCH
        assert by_code["E11.9"].suggested_code == "E11.22"
        assert by_code["N18.31"].verdict == AuditVerdict.SUPPORTED
        assert by_code["I50.9"].verdict == AuditVerdict.NOT_SUPPORTED
        assert by_code["I50.9"].reason_code == "UNCERTAIN"
        assert by_code["C18.9"].verdict == AuditVerdict.NOT_SUPPORTED
        assert by_code["C18.9"].reason_code == "HISTORICAL"

        # E11.22 was offered for E11.9 and N18.31 was submitted: nothing missed.
        assert not [f for f in result.findings if f.verdict == AuditVerdict.MISSED_HCC]
