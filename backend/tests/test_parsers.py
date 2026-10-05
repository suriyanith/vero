from pathlib import Path

import pytest

from apps.reference.parsers import (
    compute_parent_codes,
    extract_code_refs,
    parse_hcc_labels,
    parse_hcc_mappings_csv,
    parse_order_file,
    parse_tabular_xml,
)

FIXTURES = Path(__file__).parent / "fixtures"
ORDER_FILE = FIXTURES / "icd10cm_order_fixture.txt"
TABULAR_XML = FIXTURES / "icd10cm_tabular_fixture.xml"


class TestOrderFileParser:
    def test_parses_all_rows(self) -> None:
        rows = parse_order_file(ORDER_FILE)
        assert len(rows) == 21

    def test_billable_flags_and_descriptions(self) -> None:
        by_code = {row.code: row for row in parse_order_file(ORDER_FILE)}
        assert not by_code["E11"].is_billable  # category header
        assert by_code["E1122"].is_billable
        assert by_code["E1122"].long_desc == (
            "Type 2 diabetes mellitus with diabetic chronic kidney disease"
        )
        assert by_code["E1122"].short_desc.startswith("Type 2 diabetes")

    def test_seven_character_code(self) -> None:
        by_code = {row.code: row for row in parse_order_file(ORDER_FILE)}
        assert by_code["S72001A"].is_billable
        assert not by_code["S72001"].is_billable

    def test_rejects_malformed_file(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.txt"
        bad.write_text("this is not an order file\n")
        with pytest.raises(ValueError, match="layout"):
            parse_order_file(bad)


class TestCodeRefExtraction:
    def test_extracts_range_endpoints(self) -> None:
        refs = extract_code_refs(["code to identify stage (N18.1-N18.6)"])
        assert refs == ["N18.1", "N18.6"]

    def test_extracts_category_pattern(self) -> None:
        assert extract_code_refs(["type 1 diabetes mellitus (E10.-)"]) == ["E10"]

    def test_deduplicates_in_order(self) -> None:
        refs = extract_code_refs(["(Z79.4)", "also (Z79.4) and (E11.22)"])
        assert refs == ["Z79.4", "E11.22"]

    def test_ignores_plain_words(self) -> None:
        assert extract_code_refs(["no codes mentioned here"]) == []


class TestTabularXmlParser:
    def test_own_notes(self) -> None:
        notes = parse_tabular_xml(TABULAR_XML)
        e1122 = notes["E1122"]
        assert (
            "code to identify stage of chronic kidney disease (N18.1-N18.6)"
            in (e1122["use_additional"])
        )
        assert "N18.1" in e1122["use_additional_codes"]

    def test_category_notes_copied_down_to_children(self) -> None:
        notes = parse_tabular_xml(TABULAR_XML)
        # E11's Excludes1 and use-additional apply to every code below it.
        for code in ("E1121", "E1122", "E1129", "E119"):
            assert "type 1 diabetes mellitus (E10.-)" in notes[code]["excludes1"]
            assert "E10" in notes[code]["excludes1_codes"]
        # E11.22 has both the inherited Z79.4 note and its own N18 note.
        assert len(notes["E1122"]["use_additional"]) == 2

    def test_inclusion_terms_are_not_inherited(self) -> None:
        notes = parse_tabular_xml(TABULAR_XML)
        assert "inclusion_terms" not in notes["E1122"]
        assert notes["E1121"]["inclusion_terms"] == [
            "Type 2 diabetes mellitus with intercapillary glomerulosclerosis"
        ]

    def test_code_first_notes(self) -> None:
        notes = parse_tabular_xml(TABULAR_XML)
        assert "E11.22" in notes["N1831"]["code_first_codes"]


class TestHccParsers:
    def test_labels(self) -> None:
        labels = parse_hcc_labels(FIXTURES / "hcc_labels_fixture.txt")
        assert labels[37] == "Diabetes with Chronic Complications"
        assert labels[329] == "Chronic Kidney Disease, Moderate (Stage 3B)"

    def test_mappings_pick_v28_column_and_dedupe(self) -> None:
        pairs = parse_hcc_mappings_csv(FIXTURES / "hcc_mappings_fixture.csv", version="V28")
        as_dict = dict(pairs)
        assert as_dict["E1122"] == 37
        assert as_dict["N1831"] == 329
        assert "I10" not in as_dict  # no V28 HCC
        # E1122 appears twice in the file but only once with a V28 value
        assert len([c for c, _ in pairs if c == "E1122"]) == 1

    def test_unknown_version_raises(self) -> None:
        with pytest.raises(ValueError, match="V99"):
            parse_hcc_mappings_csv(FIXTURES / "hcc_mappings_fixture.csv", version="V99")


def test_compute_parent_codes() -> None:
    codes = {"E11", "E112", "E1122", "S72", "S720", "S7200", "S72001", "S72001A", "I10"}
    parents = compute_parent_codes(codes)
    assert parents["E1122"] == "E112"
    assert parents["E112"] == "E11"
    assert parents["E11"] == ""
    assert parents["S72001A"] == "S72001"
    assert parents["I10"] == ""
