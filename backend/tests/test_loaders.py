from pathlib import Path

import pytest
from django.core.management import CommandError, call_command

from apps.reference.models import CodeSetVersion, HccCategory, HccModel, Icd10Code, Icd10HccMap

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture_code_set(fy: int = 2027) -> None:
    call_command(
        "load_icd10cm",
        fy=fy,
        order_file=FIXTURES / "icd10cm_order_fixture.txt",
        tabular_xml=FIXTURES / "icd10cm_tabular_fixture.xml",
    )


def load_fixture_hcc_map() -> None:
    call_command(
        "load_hcc_map",
        model="V28",
        payment_year=2027,
        file=FIXTURES / "hcc_mappings_fixture.csv",
        labels_file=FIXTURES / "hcc_labels_fixture.txt",
    )


@pytest.mark.django_db
class TestLoadIcd10cm:
    def test_loads_codes_with_display_form_and_hierarchy(self) -> None:
        load_fixture_code_set()
        version = CodeSetVersion.objects.get(fiscal_year=2027)
        assert version.is_active
        assert version.codes.count() == 21

        e1122 = version.codes.get(code="E1122")
        assert e1122.display_code == "E11.22"
        assert e1122.is_billable
        assert e1122.category == "E11"
        assert e1122.parent_code == "E112"
        assert "E10" in e1122.notes["excludes1_codes"]

    def test_seven_char_code_inherits_ancestor_notes(self) -> None:
        load_fixture_code_set()
        s72001a = Icd10Code.objects.get(code="S72001A")
        # S72.001A has no XML node of its own; notes come from S72.001,
        # which inherited S72's Excludes1.
        assert "traumatic amputation of hip and thigh (S78.-)" in s72001a.notes["excludes1"]

    def test_idempotent(self) -> None:
        load_fixture_code_set()
        first = list(
            Icd10Code.objects.order_by("code").values(
                "code", "display_code", "is_billable", "notes", "parent_code"
            )
        )
        load_fixture_code_set()
        second = list(
            Icd10Code.objects.order_by("code").values(
                "code", "display_code", "is_billable", "notes", "parent_code"
            )
        )
        assert first == second
        assert CodeSetVersion.objects.count() == 1

    def test_newer_load_deactivates_older(self) -> None:
        load_fixture_code_set(fy=2026)
        load_fixture_code_set(fy=2027)
        assert CodeSetVersion.objects.get(fiscal_year=2026).is_active is False
        assert CodeSetVersion.objects.get(fiscal_year=2027).is_active is True

    def test_search_vector_is_built(self) -> None:
        load_fixture_code_set()
        assert not Icd10Code.objects.filter(search_vector__isnull=True).exists()


@pytest.mark.django_db
class TestLoadHccMap:
    def test_requires_code_set(self) -> None:
        with pytest.raises(CommandError, match="load_icd10cm"):
            load_fixture_hcc_map()

    def test_loads_categories_and_mappings(self) -> None:
        load_fixture_code_set()
        load_fixture_hcc_map()

        model = HccModel.objects.get(version="V28")
        assert model.is_active
        assert HccCategory.objects.filter(model=model).count() == 5

        e1122 = Icd10HccMap.objects.get(model=model, code="E1122")
        assert e1122.hcc.number == 37
        assert e1122.hcc.label == "Diabetes with Chronic Complications"
        n1831 = Icd10HccMap.objects.get(model=model, code="N1831")
        assert n1831.hcc.number == 329

    def test_idempotent(self) -> None:
        load_fixture_code_set()
        load_fixture_hcc_map()
        first = sorted(Icd10HccMap.objects.values_list("code", "hcc__number"))
        load_fixture_hcc_map()
        second = sorted(Icd10HccMap.objects.values_list("code", "hcc__number"))
        assert first == second
        assert HccModel.objects.count() == 1
