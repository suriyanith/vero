"""Full code_note runs against the Appendix C fixtures (no Django, no network)."""

from pathlib import Path

from vero_core.cli import build_fake_deps
from vero_core.interfaces import PipelineConfig
from vero_core.pipeline import code_note
from vero_core.schemas import CodingResult, ConditionStatus, Confidence

FIXTURES = Path(__file__).resolve().parents[3] / "data" / "fixtures" / "appendix_c"


def run_pipeline() -> tuple[str, CodingResult]:
    note = (FIXTURES / "note.txt").read_text(encoding="utf-8")
    result = code_note(note, build_fake_deps(FIXTURES), PipelineConfig())
    return note, result


class TestAppendixCExample:
    def test_expected_codes_with_confidence(self) -> None:
        _, result = run_pipeline()
        by_code = {s.code: s for s in result.suggestions}
        assert set(by_code) == {"E11.22", "N18.31", "R60.0"}
        assert by_code["E11.22"].confidence == Confidence.HIGH
        assert by_code["N18.31"].confidence == Confidence.HIGH
        assert by_code["R60.0"].confidence in (Confidence.HIGH, Confidence.MEDIUM)

    def test_hcc_mappings(self) -> None:
        _, result = run_pipeline()
        by_code = {s.code: s for s in result.suggestions}
        assert by_code["E11.22"].hcc_number == 37
        assert by_code["N18.31"].hcc_number == 329
        assert by_code["R60.0"].hcc_number is None

    def test_every_quote_is_a_verbatim_slice_of_the_note(self) -> None:
        note, result = run_pipeline()
        quotes = [q for s in result.suggestions for q in s.evidence] + [
            q for c in result.conditions for q in c.quotes
        ]
        assert quotes
        for quote in quotes:
            assert note[quote.start : quote.end] == quote.text

    def test_uncertain_and_historical_not_coded(self) -> None:
        _, result = run_pipeline()
        statuses = {c.label: c.status for c in result.not_coded}
        assert statuses["heart failure"] == ConditionStatus.UNCERTAIN
        assert statuses["colon cancer"] == ConditionStatus.HISTORICAL
        coded = {s.code for s in result.suggestions}
        assert "I50.9" not in coded and "C18.9" not in coded

    def test_companion_code_satisfies_use_additional(self) -> None:
        _, result = run_pipeline()
        e1122 = next(s for s in result.suggestions if s.code == "E11.22")
        assert "missing_additional_code" not in e1122.flags

    def test_nothing_dropped_and_usage_counted(self) -> None:
        _, result = run_pipeline()
        assert result.dropped == []
        assert result.usage.dropped_quotes == 0
        assert result.usage.duration_ms >= 0


def test_cli_runs_end_to_end(capsys) -> None:  # type: ignore[no-untyped-def]
    from vero_core.cli import main

    exit_code = main(
        ["code", str(FIXTURES / "note.txt"), "--llm", "fake", "--fixtures", str(FIXTURES)]
    )
    assert exit_code == 0
    output = capsys.readouterr().out
    assert '"E11.22"' in output
